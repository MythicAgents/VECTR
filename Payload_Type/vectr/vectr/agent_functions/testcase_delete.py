from mythic_container.MythicCommandBase import *
from mythic_container.MythicRPC import *
from vectr.VectrRequests import VectrAPI
from gql import gql

from pydantic import BaseModel

class TestCaseDeleteArguments(TaskArguments):
    def __init__(self, command_line, **kwargs):
        super().__init__(command_line, **kwargs)
        self.args = [
            CommandParameter(
                name="test_case_id",
                type=ParameterType.ChooseOne,
                dynamic_query_function=self.get_vectr_test_cases,
                description="VECTR test case ID",
                parameter_group_info=[ParameterGroupInfo(
                    required=True
                )]
            ),
        ]

    async def parse_arguments(self):
        if len(self.command_line) > 0:
            if self.command_line[0] == '{':
                temp_json = json.loads(self.command_line)
                if "test_case_id" in temp_json:
                    self.add_arg("test_case_id", temp_json["test_case_id"])
                else:
                    raise ValueError("Must supply a VECTR test case ID")        
            else:
                self.add_arg("test_case_id", self.command_line)
        else:
            raise ValueError("Must supply a VECTR test case ID")

    async def get_vectr_test_cases(self, callback: PTRPCDynamicQueryFunctionMessage) -> PTRPCDynamicQueryFunctionMessageResponse:
        response = PTRPCDynamicQueryFunctionMessageResponse()

        class task_data_mock(BaseModel):
            BuildParameters: list
            Secrets: dict
        
        payload_resp = await SendMythicRPCPayloadSearch(MythicRPCPayloadSearchMessage(
            CallbackID=callback.Callback,
            PayloadUUID=callback.PayloadUUID,
            PayloadTypes=[callback.PayloadType],
        ))
        if not payload_resp.Success:
            response.Error = payload_resp.Error
            return response
        if len(payload_resp.Payloads) == 0:
            response.Error = "No payloads found"
            return response

        task_data = task_data_mock(BuildParameters=payload_resp.Payloads[0].BuildParameters, Secrets=callback.Secrets)

        rest_vectr, gql_vectr = VectrAPI.initialise_vectr_connection(task_data)
        response_code, tasks = VectrAPI.get_testcases_for_campaign_by_id(gql_vectr.connection_params, gql_vectr.target_db, gql_vectr.campaign_id)
        
        if response_code != 200:
            response.Error = "Error fetching test cases"
            return response

        task_ids = []
        for task in tasks:
            task_ids.append(f"{task['id']} - {task['name']}")
        
        response.Success = True
        response.Choices = task_ids
        return response


class TestCaseDelete(CommandBase):
    cmd = "delete_testcase"
    needs_admin = False
    help_cmd = "delete_testcase -test_case_id 1"
    description = "Delete a test case from Vectr based on its ID"
    version = 2
    author = "@ajpc500"
    argument_class = TestCaseDeleteArguments
    supported_ui_features = ["vectr:testcase_delete"]
    attackmapping = []
    completion_functions = {
    }

    async def create_go_tasking(self, taskData: MythicCommandBase.PTTaskMessageAllData) -> MythicCommandBase.PTTaskCreateTaskingMessageResponse:
        test_case_id = taskData.args.get_arg("test_case_id").split(" - ")[0]

        display_params = f"with test case ID {test_case_id}"
        
        response = MythicCommandBase.PTTaskCreateTaskingMessageResponse(
            TaskID=taskData.Task.ID,
            Success=False,
            Completed=True,
            DisplayParams=display_params
        )
        try:
            rest_vectr, gql_vectr = VectrAPI.initialise_vectr_connection(taskData)
            response_code, response_data = VectrAPI.rest_delete_test_case(rest_vectr.connection_params, rest_vectr.target_db, rest_vectr.campaign_id, [test_case_id])

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
