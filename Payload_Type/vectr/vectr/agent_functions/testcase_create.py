from mythic_container.MythicCommandBase import *
from mythic_container.MythicRPC import *
from vectr.VectrRequests import VectrAPI
from gql import gql


class TestCaseCreateArguments(TaskArguments):
    def __init__(self, command_line, **kwargs):
        super().__init__(command_line, **kwargs)
        self.args = [
            CommandParameter(
                name="task_id",
                type=ParameterType.Number,
                description="Mythic task display ID",
                parameter_group_info=[ParameterGroupInfo()]
            ),
            CommandParameter(
                name="name",
                type=ParameterType.String,
                description="Name for VECTR test case (default is command executed)",
                parameter_group_info=[ParameterGroupInfo(
                    required=False
                )]
            ),
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

        display_params = f"with task ID {task_id}"
        if testcase_name is not None:
            display_params += f" and name '{testcase_name}'"
        
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
            testcase = VectrAPI.transform_mythic_task_to_testcase(gql_vectr, task_data, testcase_name)
            
            response_code, response_data = VectrAPI.create_test_cases(gql_vectr.connection_params, gql_vectr.target_db, gql_vectr.campaign_id, [testcase])

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
