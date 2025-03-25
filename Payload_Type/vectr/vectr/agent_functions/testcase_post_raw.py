from mythic_container.MythicCommandBase import *
from mythic_container.MythicRPC import *
from vectr.VectrRequests import VectrAPI
from gql import gql

class TestCasePostRawJsonArguments(TaskArguments):
    def __init__(self, command_line, **kwargs):
        super().__init__(command_line, **kwargs)
        self.args = [
            CommandParameter(
                name="test_case_json",
                type=ParameterType.String,
                description="A raw VECTR test case JSON",
                parameter_group_info=[ParameterGroupInfo(
                    required=True
                )]
            )
        ]

    async def parse_arguments(self):
        if len(self.command_line) == 0:
            raise ValueError("Must supply a VECTR test case and new name")
        raise ValueError("Must supply named arguments or use the modal")

    async def parse_dictionary(self, dictionary_arguments):
        if "test_case_json" in dictionary_arguments:
            self.add_arg("test_case_json", dictionary_arguments["test_case_json"])


class TestCasePostRawJson(CommandBase):
    cmd = "post_raw_testcase_json"
    needs_admin = False
    help_cmd = "post_raw_testcase_json -test_case_json '{}'"
    description = "POST raw JSON for a VECTR test case"
    version = 2
    author = "@ajpc500"
    argument_class = TestCasePostRawJsonArguments
    attackmapping = []
    completion_functions = {
    }

    async def create_go_tasking(self, taskData: MythicCommandBase.PTTaskMessageAllData) -> MythicCommandBase.PTTaskCreateTaskingMessageResponse:
        test_case_json = taskData.args.get_arg("test_case_json")

        response = MythicCommandBase.PTTaskCreateTaskingMessageResponse(
            TaskID=taskData.Task.ID,
            Success=False,
            Completed=True,
            DisplayParams=f""
        )
        try:
            rest_vectr, gql_vectr = VectrAPI.initialise_vectr_connection(taskData)
            
            try:
                test_case_json = json.loads(test_case_json)
            except json.JSONDecodeError as e:
                raise ValueError(f"test_case_json is not valid JSON: {e}")
            
            response_code, response_data = VectrAPI.rest_update_test_case(
                rest_vectr.connection_params, rest_vectr.target_db, test_case_json
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
