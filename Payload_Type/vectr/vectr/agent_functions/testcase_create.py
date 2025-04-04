from mythic_container.MythicCommandBase import *
from mythic_container.MythicRPC import *
from vectr.VectrRequests import VectrAPI
from gql import gql

from pydantic import BaseModel

VECTR_TAG_NAME = "SentToVECTR"

class TestCaseCreateArguments(TaskArguments):
    def __init__(self, command_line, **kwargs):
        super().__init__(command_line, **kwargs)
        self.args = [
            CommandParameter(
                name="task_id",
                type=ParameterType.Number,
                description="Mythic task display ID",
                parameter_group_info=[ParameterGroupInfo(
                    required=True,
                    ui_position=0,
                )]
            ),
            CommandParameter(
                name="name",
                type=ParameterType.String,
                description="Name for VECTR test case (default is command executed)",
                parameter_group_info=[ParameterGroupInfo(
                    required=False,
                    ui_position=1
                )]
            ),
            CommandParameter(
                name="tactic_id",
                type=ParameterType.ChooseOne,
                dynamic_query_function=self.get_vectr_mitre_tactics,
                description="MITRE ATT&CK Enterprise tactic ID",
                parameter_group_info=[ParameterGroupInfo(
                    required=False,
                    ui_position=2
                )]
            ),
            CommandParameter(
                name="technique_id",
                type=ParameterType.ChooseOne,
                dynamic_query_function=self.get_vectr_mitre_techniques,
                description="MITRE ATT&CK Enterprise technique ID",
                parameter_group_info=[ParameterGroupInfo(
                    required=False,
                    ui_position=3
                )]
            ),
            CommandParameter(
                name="force_create",
                type=ParameterType.Boolean,
                description="Force the creation of a VECTR test case for Mythic tasks that have already been imported",
                default_value=False,
                parameter_group_info=[ParameterGroupInfo(
                    required=False,
                    ui_position=4
                )]
            )
        ]

    async def parse_arguments(self):
        if len(self.command_line) == 0:
            raise ValueError("Must supply a Mythic task ID")
        raise ValueError("Must supply named arguments or use the modal")

    async def parse_dictionary(self, dictionary_arguments):
        if "task_id" in dictionary_arguments:
            self.add_arg("task_id", dictionary_arguments["task_id"])
        if "name" in dictionary_arguments:
            self.add_arg("name", dictionary_arguments["name"])
        if "technique_id" in dictionary_arguments:
            self.add_arg("technique_id", dictionary_arguments["technique_id"])
        if "tactic_id" in dictionary_arguments:
            self.add_arg("tactic_id", dictionary_arguments["tactic_id"])      
        if "force_create" in dictionary_arguments:
            self.add_arg("force_create", dictionary_arguments["force_create"])  

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

        mitre_ids = [""]
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

        mitre_ids = [""]
        tactics.sort(key=lambda x: x['mitreId'])

        for tactic in tactics:
            mitre_ids.append(f"{tactic['mitreId']} - {tactic['name']}")       

        response.Success = True
        response.Choices = mitre_ids
        return response



class TestCaseCreate(CommandBase):
    cmd = "create_testcase"
    needs_admin = False
    help_cmd = "create_testcase -task_id 1 -name 'custom name'"
    description = "Add a new test case to Vectr based on Mythic task ID"
    version = 2
    author = "@ajpc500"
    argument_class = TestCaseCreateArguments
    supported_ui_features = ["vectr:testcase_create"]
    browser_script = BrowserScript(script_name="testcase_create", author="@ajpc500")
    attackmapping = []
    completion_functions = {
    }

    async def create_go_tasking(self, taskData: MythicCommandBase.PTTaskMessageAllData) -> MythicCommandBase.PTTaskCreateTaskingMessageResponse:
        task_id = taskData.args.get_arg("task_id")
        testcase_name = taskData.args.get_arg("name")
        force_create = taskData.args.get_arg("force_create")
        task_has_existing_tag = False

        if taskData.args.get_arg("technique_id"):
            mitre_technique_id = taskData.args.get_arg("technique_id").split(" - ")[0].upper()
            mitre_technique_name = taskData.args.get_arg("technique_id").split(" - ")[1]
        else:
            mitre_technique_id = None
        
        if taskData.args.get_arg("tactic_id"):
            mitre_tactic_id = taskData.args.get_arg("tactic_id").split(" - ")[0].upper()
            mitre_tactic_name = taskData.args.get_arg("tactic_id").split(" - ")[1]
        else:
            mitre_tactic_id = None
            mitre_tactic_name = None

        display_params = f"with task ID {task_id}"
        if testcase_name:
            display_params += f" and name '{testcase_name}'"

        if mitre_technique_id or mitre_tactic_name:
            mitre_display_values = [mitre_technique_id, mitre_tactic_name]
            display_params += f" (ATT&CK: {', '.join([x for x in mitre_display_values if x is not None])})"
        
        if force_create:
            display_params += " (force creating)"

        response = MythicCommandBase.PTTaskCreateTaskingMessageResponse(
            TaskID=taskData.Task.ID,
            Success=False,
            Completed=True,
            DisplayParams=display_params
        )
        try:
            # We'll create task_data to hold the task and any responses.
            task_data = {}

            # Fetch the task from Mythic
            task_search_response = await SendMythicRPCTaskSearch(MythicRPCTaskSearchMessage(TaskID=taskData.Task.ID, SearchTaskDisplayID=int(task_id)))
             
            #  If we have a task, we'll add it to the task_data
            if task_search_response.Success and len(task_search_response.Tasks) > 0:
                data = task_search_response.Tasks[0]
                task_data['task'] = data.to_json()
            else:
                # We can have no responses, but no task is a deal breaker so we'll return an error.
                response.TaskStatus = "Error: Task ID not found"
                response.Success = False
                return response

            # We'll fetch the tags on the task before we continue to make sure it isn't a duplicate
            tag_search_response = await SendMythicRPCTagSearch(MythicRPCTagSearchMessage(
                TaskID=taskData.Task.ID, 
                SearchTagTaskID=int(task_id),
            ))
            if tag_search_response.Success and len(tag_search_response.Tags) > 0:
                if any(VECTR_TAG_NAME in tag.TagType.Name for tag in tag_search_response.Tags):
                    if not force_create:
                        await SendMythicRPCResponseCreate(MythicRPCResponseCreateMessage(
                            TaskID=taskData.Task.ID,
                            Response=f"Error: Task has the '{VECTR_TAG_NAME}' tag, and has already been imported into VECTR. Use the -force_create flag to create a new test case anyway.".encode("UTF8"),
                        ))
                        response.TaskStatus = f"Error: Task already imported into VECTR."
                        response.Success = False
                        return response
                    else:
                        task_has_existing_tag = True

            task_callback_id = task_data['task']['callback_id']
            task_name = task_data['task']['command_name']
            payload_type = task_data['task']['payload_type']
            # Let's get more info on the task itself for a description
            task_detail_search_response = await SendMythicRPCCommandSearch(MythicRPCCommandSearchMessage(
                SearchPayloadTypeName=payload_type,
                SearchCommandNames=[task_name]
            ))
            if task_detail_search_response.Success and len(task_detail_search_response.Commands) > 0:
                task_data['task_metadata'] = task_detail_search_response.Commands[0].to_json()

            # Let's get more info on the callback that ran the task to populate target data
            callback_search_response = await SendMythicRPCCallbackSearch(MythicRPCCallbackSearchMessage(
                AgentCallbackID=int(task_callback_id)
            ))
            if callback_search_response.Success and len(callback_search_response.Results) > 0:
                for result in callback_search_response.Results:
                    if result.ID == task_callback_id:
                        task_data['callback'] = result.to_json()
                        break

            # Fetch the responses from Mythic
            task_data['responses'] = []
            response_search_response = await SendMythicRPCResponseSearch(MythicRPCResponseSearchMessage(TaskID=int(task_id)))

            # If we have responses, we'll add them to the task_data
            if response_search_response.Success and len(response_search_response.Responses) > 0:
                task_responses = response_search_response.Responses
                for task_response in task_responses:
                    task_data['responses'].append(task_response.to_json())
            
            rest_vectr, gql_vectr = VectrAPI.initialise_vectr_connection(taskData)
            testcase = VectrAPI.transform_mythic_task_to_testcase(gql_vectr, task_data, testcase_name, mitre_technique_id, mitre_tactic_name)

            response_code, response_data = VectrAPI.create_test_cases(gql_vectr.connection_params, gql_vectr.target_db, gql_vectr.campaign_id, [testcase])

            if response_code == 200 and not task_has_existing_tag:
                try:
                    # add tag to prevent accidental re-importing later on
                    create_tag_response = await SendMythicRPCTagTypeGetOrCreate(MythicRPCTagTypeGetOrCreateMessage(
                        TaskID=taskData.Task.ID,
                        GetOrCreateTagTypeName=VECTR_TAG_NAME,
                        GetOrCreateTagTypeDescription="Tasks that have been imported into VECTR",
                        GetOrCreateTagTypeColor="#ff00fb"
                    ))
                    if create_tag_response.TagType:
                        tag_type_id = create_tag_response.TagType.ID
                        add_tag_to_task_response = await SendMythicRPCTagCreate(MythicRPCTagCreateMessage(
                            TagTypeID=int(tag_type_id),
                            TaskID=int(task_id),
                            Data={
                                "test_case_id": response_data["testcases"][0]['id'],
                                "test_case_name": testcase.name,
                                "added_by": task_data['task'].get('operator_username', "")
                            }
                        ))
                        if not add_tag_to_task_response.Success:
                            raise Exception(f"Add tag failed. {add_tag_to_task_response.Error}")
                    else:
                        raise Exception(f"Create or get tag failed. {create_tag_response.Error}")
                except Exception as e:
                    await SendMythicRPCResponseCreate(MythicRPCResponseCreateMessage(
                        TaskID=taskData.Task.ID,
                        Response=f"Error: Successfully created test case in VECTR, but failed to add the '{VECTR_TAG_NAME}' tag to Mythic task '{task_id}'. Error: {e}".encode("UTF8"),
                    ))
                    response.TaskStatus = f"Error: Tag assignment failed."
                    response.Success = False
                    return response
                    

            return await VectrAPI.process_standard_response(
                response_code=response_code,
                response_data=response_data,
                taskData=taskData,
                response=response
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
