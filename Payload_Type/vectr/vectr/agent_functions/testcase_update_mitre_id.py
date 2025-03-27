from mythic_container.MythicCommandBase import *
from mythic_container.MythicRPC import *
from vectr.VectrRequests import VectrAPI
from gql import gql

from pydantic import BaseModel

class TestCaseUpdateNameArguments(TaskArguments):
    def __init__(self, command_line, **kwargs):
        super().__init__(command_line, **kwargs)
        self.args = [
            CommandParameter(
                name="test_case_id",
                type=ParameterType.ChooseOne,
                dynamic_query_function=self.get_vectr_test_cases,
                description="VECTR test case ID",
                parameter_group_info=[ParameterGroupInfo(
                    required=True,
                    ui_position=0
                )]
            ),
            CommandParameter(
                name="technique_id",
                type=ParameterType.ChooseOne,
                dynamic_query_function=self.get_vectr_mitre_techniques,
                description="MITRE ATT&CK Enterprise technique ID",
                parameter_group_info=[ParameterGroupInfo(
                    required=True,
                    ui_position=1
                )]
            ),
            CommandParameter(
                name="tactic_id",
                type=ParameterType.ChooseOne,
                dynamic_query_function=self.get_vectr_mitre_tactics,
                description="MITRE ATT&CK Enterprise tactic ID",
                parameter_group_info=[ParameterGroupInfo(
                    required=True,
                    ui_position=2
                )]
            )
        ]

    async def parse_arguments(self):
        if len(self.command_line) == 0:
            raise ValueError("Must supply a VECTR test case and new name")
        raise ValueError("Must supply named arguments or use the modal")

    async def parse_dictionary(self, dictionary_arguments):
        if "test_case_id" in dictionary_arguments:
            self.add_arg("test_case_id", dictionary_arguments["test_case_id"])
        if "technique_id" in dictionary_arguments:
            self.add_arg("technique_id", dictionary_arguments["technique_id"])
        if "tactic_id" in dictionary_arguments:
            self.add_arg("tactic_id", dictionary_arguments["tactic_id"])

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
    
    
    async def get_vectr_mitre_techniques(self, callback: PTRPCDynamicQueryFunctionMessage) -> PTRPCDynamicQueryFunctionMessageResponse:
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
        response_code, techniques = VectrAPI.rest_get_mitre_techniques(rest_vectr.connection_params)
        
        if response_code != 200:
            response.Error = "Error fetching test cases"
            return response

        mitre_ids = []
        techniques.sort(key=lambda x: x['mitreId'])

        for technique in techniques:
            mitre_ids.append(f"{technique['mitreId']} - {technique['name']}")       

        response.Success = True
        response.Choices = mitre_ids
        return response
    
    
    async def get_vectr_mitre_tactics(self, callback: PTRPCDynamicQueryFunctionMessage) -> PTRPCDynamicQueryFunctionMessageResponse:
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
        response_code, tactics = VectrAPI.rest_get_mitre_tactics(rest_vectr.connection_params, rest_vectr.target_db, rest_vectr.assessment_id)
        
        if response_code != 200:
            response.Error = "Error fetching test cases"
            return response

        mitre_ids = []
        tactics.sort(key=lambda x: x['mitreId'])

        for tactic in tactics:
            mitre_ids.append(f"{tactic['mitreId']} - {tactic['name']}")       

        response.Success = True
        response.Choices = mitre_ids
        return response


class TestCaseUpdateName(CommandBase):
    cmd = "update_testcase_mitre_id"
    needs_admin = False
    help_cmd = "update_testcase_mitre_id -test_case_id 1 -technique_id T1059 -tactic_id TA0001"
    description = "Update the MITRE tactic and technique of a test case in VECTR"
    version = 2
    author = "@ajpc500"
    supported_ui_features = ["vectr:testcase_mitre_update"]
    argument_class = TestCaseUpdateNameArguments
    attackmapping = []
    completion_functions = {
    }

    async def create_go_tasking(self, taskData: MythicCommandBase.PTTaskMessageAllData) -> MythicCommandBase.PTTaskCreateTaskingMessageResponse:
        test_case_id = taskData.args.get_arg("test_case_id").split(" - ")[0]
        mitre_technique_id = taskData.args.get_arg("technique_id").split(" - ")[0].upper()
        mitre_technique_name = taskData.args.get_arg("technique_id").split(" - ")[1]
        mitre_tactic_id = taskData.args.get_arg("tactic_id").split(" - ")[0].upper()
    
        response = MythicCommandBase.PTTaskCreateTaskingMessageResponse(
            TaskID=taskData.Task.ID,
            Success=False,
            Completed=True,
            DisplayParams=f"for {test_case_id} to '{mitre_technique_id}'"
        )
        try:
            rest_vectr, gql_vectr = VectrAPI.initialise_vectr_connection(taskData)
            response_code, response_data = VectrAPI.rest_get_test_case(
                rest_vectr.connection_params, 
                rest_vectr.target_db, 
                test_case_id
            )
            if response_code != 200:
                raise Exception(response_data)

            # Get MITRE tactics back so we can convert ID to identifier
            response_code, tactics = VectrAPI.rest_get_mitre_tactics(rest_vectr.connection_params, rest_vectr.target_db, rest_vectr.assessment_id)

            if response_code != 200:
                raise Exception(response_data)

            tactic_id = ""
            for tactic in tactics:
                if tactic['mitreId'] == mitre_tactic_id:
                    tactic_id = tactic['id']

            if not response_data.get('redTeam', {}).get('mitreId', None):
                raise Exception("No redteam.mitreId field found for test case")

            response_data['redTeam']['mitreId'] = mitre_technique_id.upper()
            response_data['redTeam']['method'] = mitre_technique_name

            if tactic_id:
                response_data['phaseId'] = tactic_id

            response_code, response_data = VectrAPI.rest_update_test_case(
                rest_vectr.connection_params, rest_vectr.target_db, response_data
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
