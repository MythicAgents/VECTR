from mythic_container.MythicCommandBase import *
from mythic_container.MythicRPC import *
from vectr.VectrRequests import VectrAPI
from gql import gql


class TestCaseArtifactUploadArguments(TaskArguments):

    def __init__(self, command_line, **kwargs):
        super().__init__(command_line, **kwargs)
        self.args = [
            CommandParameter(
                name="file",
                type=ParameterType.File,
                parameter_group_info=[ParameterGroupInfo(
                    required=True,
                    ui_position=1,
                    group_name="Manually Upload New File"
                )]
            ),
            CommandParameter(
                name="filename",
                type=ParameterType.ChooseOne,
                dynamic_query_function=self.get_files,
                parameter_group_info=[ParameterGroupInfo(
                    required=True,
                    ui_position=1,
                    group_name="Select Mythic File to Upload"
                )]
            ),
            CommandParameter(
                name="description",
                type=ParameterType.String,
                default_value="",
                parameter_group_info=[
                    ParameterGroupInfo(
                        required=False,
                        ui_position=2,
                        group_name="Manually Upload New File"
                    ),
                    ParameterGroupInfo(
                        required=False,
                        ui_position=2,
                        group_name="Select Mythic File to Upload"
                    )
                ]
            ),
            CommandParameter(
                name="test_case_id",
                type=ParameterType.String,
                parameter_group_info=[
                    ParameterGroupInfo(
                        required=True,
                        ui_position=3,
                        group_name="Manually Upload New File"
                    ),
                    ParameterGroupInfo(
                        required=True,
                        ui_position=3,
                        group_name="Select Mythic File to Upload"
                    )
                ]
            )
        ]

    async def parse_arguments(self):
        self.load_args_from_json_string(self.command_line)

    async def parse_dictionary(self, dictionary_arguments):
        self.load_args_from_dictionary(dictionary=dictionary_arguments)


    async def get_files(self, callback: PTRPCDynamicQueryFunctionMessage) -> PTRPCDynamicQueryFunctionMessageResponse:
        response = PTRPCDynamicQueryFunctionMessageResponse()
        file_resp = await SendMythicRPCFileSearch(MythicRPCFileSearchMessage(
            CallbackID=callback.Callback,
            LimitByCallback=False,
            IsDownloadFromAgent=True,
            IsScreenshot=False,
            IsPayload=False,
            Filename="",
        ))
        if file_resp.Success:
            file_names = []
            for f in file_resp.Files:
                if f.Filename not in file_names:
                    file_names.append(f.Filename)
            response.Success = True
            response.Choices = file_names
            return response
        else:
            await SendMythicRPCOperationEventLogCreate(MythicRPCOperationEventLogCreateMessage(
                CallbackId=callback.Callback,
                Message=f"Failed to get files: {file_resp.Error}",
                MessageLevel="warning"
            ))
            response.Error = f"Failed to get files: {file_resp.Error}"
            return response


class TestCaseArtifactUpload(CommandBase):
    cmd = "upload_testcase_artifact"
    needs_admin = False
    help_cmd = "upload_testcase_artifact"
    description = "Upload a file as an execution artifact for a VECTR test case"
    version = 2
    author = "@ajpc500"
    argument_class = TestCaseArtifactUploadArguments
    supported_ui_features = ["vectr:testcase_artifact_upload"]
    attackmapping = []
    completion_functions = {
    }

    async def create_go_tasking(self, taskData: MythicCommandBase.PTTaskMessageAllData) -> MythicCommandBase.PTTaskCreateTaskingMessageResponse:
        response = MythicCommandBase.PTTaskCreateTaskingMessageResponse(
            TaskID=taskData.Task.ID,
            Success=False,
            Completed=True,
            DisplayParams=f""
        )
        try:
            fileMetadata = None
            if taskData.args.get_parameter_group_name() == "Manually Upload New File":
                searchedFile = await SendMythicRPCFileSearch(MythicRPCFileSearchMessage(
                    AgentFileID=taskData.args.get_arg("file")
                ))
                if not searchedFile.Success:
                    raise Exception(searchedFile.Error)
                if len(searchedFile.Files) != 1:
                    raise Exception("Failed to get file back from Mythic")
                fileMetadata = searchedFile.Files[0]

            else:
                searchedFile = await SendMythicRPCFileSearch(MythicRPCFileSearchMessage(
                    TaskID=taskData.Task.ID,
                    Filename=taskData.args.get_arg("filename"),
                    LimitByCallback=False,
                    MaxResults=1
                ))
                if not searchedFile.Success:
                    raise Exception(searchedFile.Error)
                if len(searchedFile.Files) != 1:
                    raise Exception("Failed to get file back from Mythic")
                fileMetadata = searchedFile.Files[0]

            filename = fileMetadata.Filename

            fileContentsResp = await SendMythicRPCFileGetContent(MythicRPCFileGetContentMessage(
                AgentFileId=fileMetadata.AgentFileId
            ))
            if not fileContentsResp.Success:
                raise Exception(fileContentsResp.Error)
            
            encrypted_base64, key_base64, nonce_base64, data_hash = VectrAPI.encrypt_execution_artifact(fileContentsResp.Content)

            rest_vectr, gql_vectr = VectrAPI.initialise_vectr_connection(taskData)

            response_code, response_data = VectrAPI.rest_upload_execution_artifact(
                rest_vectr.connection_params,
                encrypted_base64,
                key_base64,
                nonce_base64,
                len(fileContentsResp.Content),
                data_hash,
                filename,
                taskData.args.get_arg("description")
            )
            if response_code != 200:
                raise Exception(response_data)

            test_case_id = taskData.args.get_arg("test_case_id")
            execution_artifact_id = response_data['data']['savedData']['id']
            
            response_code, response_data = VectrAPI.rest_add_execution_artifact_to_test_case(
                rest_vectr.connection_params, rest_vectr.target_db, test_case_id, execution_artifact_id
            )

            return await VectrAPI.process_standard_response(
                response_code=response_code,
                response_data=response_data['message'],
                taskData=taskData,
                response=response,
                as_json=False
            )

        except Exception as e:
            await SendMythicRPCResponseCreate(MythicRPCResponseCreateMessage(
                TaskID=taskData.Task.ID,
                Response=f"{e}".encode("UTF8"),
            ))
            response.TaskStatus = "Error: Vectr Access Error"
            response.Success = False
        return response

    async def process_response(self, task: PTTaskMessageAllData, response: any) -> PTTaskProcessResponseMessageResponse:
        resp = PTTaskProcessResponseMessageResponse(TaskID=task.Task.ID, Success=True)
        return resp
