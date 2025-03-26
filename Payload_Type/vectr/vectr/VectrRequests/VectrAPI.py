from mythic_container.MythicCommandBase import *
from vectr.VectrRequests.VectrAPIClasses import *
from mythic_container.MythicRPC import *

import nacl.utils
from nacl.encoding import Base64Encoder
from nacl.hash import generichash
from nacl.secret import SecretBox

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timezone
import requests

# REMOVE ME
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VECTR_API_KEY = "VECTR_API_KEY"

def check_valid_values(api_key, url, org_name, assessment_name, campaign_name, target_db) -> bool:
    if api_key == "" or api_key is None:
        logger.error("missing api key")
        return False
    if url == "" or url is None:
        logger.error("missing url")
        return False
    if org_name == "" or org_name is None:
        logger.error("missing org name")
        return False
    if assessment_name == "" or assessment_name is None:
        logger.error("missing assessment name")
        return False
    if campaign_name == "" or campaign_name is None:
        logger.error("missing campaign name")
        return False
    if target_db == "" or target_db is None:
        logger.error("missing target db")
        return False
    return True


def get_client(connection_params: VectrGQLConnParams):
    transport = RequestsHTTPTransport(
        url=connection_params.vectr_gql_url, verify=False, retries=1,
        headers={"Authorization": "VEC1 " + connection_params.api_key}
    )
    return Client(transport=transport, fetch_schema_from_transport=False)


def initialise_vectr_connection(taskData):
    print("\n[*] Initialising VECTR API:")
    
    for buildParam in taskData.BuildParameters:
        if buildParam.Name == "URL":
            url = buildParam.Value
        if buildParam.Name == "org_name":
            org_name = buildParam.Value
        if buildParam.Name == "assessment_name":
            assessment_name = buildParam.Value
        if buildParam.Name == "campaign_name":
            campaign_name = buildParam.Value
        if buildParam.Name == "target_db":
            target_db = buildParam.Value
    if VECTR_API_KEY in taskData.Secrets:
        api_key = taskData.Secrets[VECTR_API_KEY]
    if not check_valid_values(api_key, url, org_name, assessment_name, campaign_name, target_db):
        return 500, f"Missing {VECTR_API_KEY} in User settings or missing Vectr URL, org name, assessment name, campaign name or target db."
    
    connection_params = VectrGQLConnParams(
        api_key=api_key,
        vectr_gql_url=url + "/graphql"
    )

    rest_connection_params = VectrRESTConnParams(
        api_key=api_key,
        vectr_rest_url=url
    )

    org_id = get_org_id_for_campaign_and_assessment_data(
        connection_params=connection_params,
        org_name=org_name
    )
    print(f"  - Assessment Name: {assessment_name}")
    print(f"  - Target DB: {target_db}")

    try:
        assessment_id = get_assessment_by_name(connection_params, target_db, assessment_name)
        print(f"  - Using existing assessment with ID: {assessment_id}")
    except RuntimeError as e:
        created_assessment_detail = create_assessment(connection_params, target_db, org_id, assessment_name)
        assessment_id = created_assessment_detail.get(assessment_name).get("id")
        logger.info(f"  - Created assessment with ID: {assessment_id}")

    try:
        response_code, response_data = get_campaign_by_name(connection_params, target_db, campaign_name)
        if response_code != 200:
            raise RuntimeError(f"Error getting campaign by name: {response_data}")
        campaign_id = response_data
        print(f"  - Using existing campaign with ID: {campaign_id}\n")
    except RuntimeError as e:
        cpgn = { campaign_name: Campaign(name=campaign_name, test_cases=[]) }
        created_campaigns = create_campaigns(
            connection_params,
            target_db,
            org_id,
            cpgn,
            str(assessment_id)
        )
        campaign_id = created_campaigns.get(campaign_name).get("id")
        logger.info(f"  - Created campaign with ID: {campaign_id}\n")
    
    return vectr_connection(org_name, rest_connection_params, target_db, campaign_name, campaign_id, assessment_id), vectr_connection(org_name, connection_params, target_db, campaign_name, campaign_id, assessment_id)



def create_assessment(connection_params: VectrGQLConnParams,
                      db: str,
                      org_id: str,
                      assessment_name: str) -> Dict[str, dict]:
    """Creates a named VECTR Assessment (Assessment Group) in the target database

    Parameters
    ----------
    connection_params : VectrGQLConnParams
        Connection parameters for the target VECTR instance including api key and url
    db : str
        The database target where the assessment will be created
        This only includes selectable databases, template operations are separate
    org_id : str
        The org_id to which this Assessment will belong
    assessment_name: str
        The name of the Assessment to be created

    Returns
    -------
    Dict[str, dict]
        An Assessment name-keyed dict of objects with the id and name of a created Assessment
    """
    client = get_client(connection_params)
    assessment_mutation = gql(
        """
        mutation ($input: CreateAssessmentInput!) {
          assessment {
            create(input: $input) {
              assessments {
                id, name, description, createTime
              }
            }
          }
        }
        """
    )

    assessment_vars = {
        "input": {
            "db": db,
            "assessmentData": [
                {
                    "name": assessment_name,
                    "organizationIds": [org_id]
                }
            ]
        }
    }

    assessments = {}

    result = client.execute(assessment_mutation, variable_values=assessment_vars)
    if "assessment" in result.keys():
        assessment_type_res = result["assessment"]
        if "create" in assessment_type_res:
            create_res = assessment_type_res["create"]
            if "assessments" in create_res:
                assessments_created = create_res["assessments"]

                for assessment in assessments_created:
                    assessments[assessment["name"]] = {"id": assessment["id"], "name": assessment["name"]}

    return assessments


def create_campaigns(connection_params: VectrGQLConnParams,
                     db: str,
                     org_id: str,
                     campaigns: Dict[str, Campaign],
                     parent_assessment_id: str) -> Dict[str, dict]:
    """Creates VECTR Campaigns in the target Assessment and Database

        Parameters
        ----------
        connection_params : VectrGQLConnParams
            Connection parameters for the target VECTR instance including api key and url
        db : str
            The database target where the Campaigns will be created
            This only includes selectable databases, template operations are separate
        org_id : str
            The org_id to which the Campaigns will belong
        campaigns: Dict[str, Campaign]
            Campaigns to be created
        parent_assessment_id: str
            The ID of the parent Assessment for the Campaigns

        Returns
        -------
        Dict[str, dict]
            A Campaign name-keyed dict of objects with the id and name of created Campaigns
        """
    client = get_client(connection_params)
    campaign_mutation = gql(
        """
        mutation ($input: CreateCampaignInput!) {
          campaign {
            create(input: $input) {
              campaigns {
                id, name, createTime
              }
            }
          }
        }
        """
    )

    campaign_data = []
    for campaign_name in campaigns.keys():
        campaign_data.append({
            "name": campaign_name,
            "organizationIds": [org_id]
        })

    campaign_vars = {
        "input": {
            "db": db,
            "assessmentId": parent_assessment_id,
            "campaignData": campaign_data
        }
    }

    campaigns = {}

    result = client.execute(campaign_mutation, variable_values=campaign_vars)

    if "campaign" in result.keys():
        campaign_type_res = result["campaign"]
        if "create" in campaign_type_res:
            create_res = campaign_type_res["create"]
            if "campaigns" in create_res:
                campaigns_created = create_res["campaigns"]

                for campaign in campaigns_created:
                    campaigns[campaign["name"]] = {"id": campaign["id"], "name": campaign["name"]}

    return campaigns

def rest_delete_test_case(connection_params: VectrRESTConnParams,
                      db: str,
                      campaign_id: str,
                      test_cases: List[int]):

    response = requests.post(
        connection_params.vectr_rest_url + "/testcases/delete?databaseName=" + db, 
        json={
            "includes":{
                "ids": [ str(tc) for tc in test_cases ]
            }
        }, 
        headers={"Authorization": "VEC1 " + connection_params.api_key},
        verify=False
    )
    return response.status_code, response.json()


def rest_upload_execution_artifact(
    connection_params: VectrRESTConnParams,
    encrypted_base64: str,
    key_base64: str,
    nonce_base64: str,
    file_size: int,
    file_hash: str,
    file_name: str,
    description: str,
    ):
    
    response = requests.post(
        connection_params.vectr_rest_url + "/executionArtifacts/uploadDocument?collectionName=ExecutionArtifacts", 
        json={
            "documentContents": encrypted_base64,
            "overwriteExisting": True,
            "allowDupeHash": True,
            "metadata":{
                "description": description,
                "version": "latest",
                "encryptionKey": key_base64,
                "hash": file_hash,
                "filename": file_name,
                "label": file_name,
                "nonce": nonce_base64,
                "size": file_size
            }
        },
        headers={"Authorization": "VEC1 " + connection_params.api_key},
        verify=False
    )
    return response.status_code, response.json()


def rest_get_test_case(connection_params: VectrRESTConnParams, 
                       db: str,
                       test_case_id: int):
    response = requests.get(
        connection_params.vectr_rest_url + "/testcases/" + str(test_case_id) + "?databaseName=" + db,
        headers={"Authorization": "VEC1 " + connection_params.api_key},
        verify=False
    )
    test_case_response = response.json()
    if len(test_case_response.get("data"))==1:
        test_case_data = test_case_response.get("data")[0]
    else:
        raise Exception("Error getting test case data")
    
    return response.status_code, test_case_data 


def rest_update_test_case(connection_params: VectrRESTConnParams,
                        db: str,
                        test_case: dict):
    response = requests.put(
        connection_params.vectr_rest_url + "/testcases?databaseName=" + db,
        json=[{
            "timelineEventData": [],
            "testCaseData": test_case
        }],
        headers={"Authorization": "VEC1 " + connection_params.api_key},
        verify=False
    )
    return response.status_code, response.json()


def rest_add_execution_artifact_to_test_case(connection_params: VectrRESTConnParams, 
                                             db: str,
                                             test_case_id: int, 
                                             execution_artifact_id: int):
    response_code, raw_test_case = rest_get_test_case(connection_params, db, test_case_id)
    
    if not raw_test_case:
        500, "Error getting test case data"

    raw_test_case["redTeam"]["executionArtifactIds"].append(str(execution_artifact_id))

    return rest_update_test_case(connection_params, db, raw_test_case)


def rest_get_mitre_techniques(connection_params: VectrRESTConnParams):
    response = requests.get(
        connection_params.vectr_rest_url + "/mitre/getTechniqueIdMap?mitreFramework=ENTERPRISE",
        headers={"Authorization": "VEC1 " + connection_params.api_key},
        verify=False
    )
    if not 'data' in response.json():
        return 500, "Error getting MITRE techniques"
    
    data = response.json()['data']
    
    techniques = []
    for technique, mitre_ids in data.items():
        for mitre_id in mitre_ids:
            techniques.append({ "name": technique, "mitreId": mitre_id })

    return response.status_code, techniques

def rest_get_mitre_tactics(connection_params: VectrRESTConnParams, db: str, assessment_id: int):
        
    # https://vectr:8081/sra-purpletools-rest/phases/getAssessmentActivePhases?databaseName=MYTHIC&assessmentId=95

    # Assessment specific active phases
    response = requests.get(
        connection_params.vectr_rest_url + "/phases/getAssessmentActivePhases?databaseName=" + db + "&assessmentId=" + str(assessment_id),
        headers={"Authorization": "VEC1 " + connection_params.api_key},
        verify=False
    )
    if not 'data' in response.json():
        return 500, "Error getting MITRE techniques"

    active_phases = response.json()['data']

    # General MITRE tactic metadata
    response = requests.get(
        connection_params.vectr_rest_url + "/mitre/tacticIdMap?mitreFramework=ENTERPRISE",
        headers={"Authorization": "VEC1 " + connection_params.api_key},
        verify=False
    )
    if not 'data' in response.json():
        return 500, "Error getting MITRE techniques"
    
    data = response.json()['data']
    
    tactics = []
    for mitre_identifier, mitre_data in data.items():
        id = ""
        for phase in active_phases:
            if phase.get('mitreTactics', []):
                if mitre_identifier in phase.get('mitreTactics', []):
                    id = phase['id']
                    break

        tactic_id = mitre_data['externalId']
        tactic_name = mitre_data['name']
        description = mitre_data['description']
        short_name = mitre_data['shortName']
        
        tactics.append({ 
            "id": id,
            "mitreId": tactic_id,
            "name": tactic_name,
            "description": description,
            "shortName": short_name,
            "mitreIdentifier": mitre_identifier
        })

    return response.status_code, tactics


def create_test_cases(connection_params: VectrGQLConnParams,
                      db: str,
                      campaign_id: str,
                      test_cases: Dict[str, TestCase]) -> Dict[str, dict]:
    """Creates VECTR Test Cases in the target Campaign and Database

        Parameters
        ----------
        connection_params : VectrGQLConnParams
            Connection parameters for the target VECTR instance including api key and url
        db : str
            The database target where the Campaigns will be created
            This only includes selectable databases, template operations are separate
        campaign_id : str
            The Campaign ID to which the Test Cases will belong
        test_cases: Dict[str, TestCase]
            TestCases to be created

        Returns
        -------
        Dict[str, dict]
            A Test Case name-keyed dict of objects with the id and name of created Test Cases
        """
    try:
        client = get_client(connection_params)
        test_case_mutation = gql(
            """
            mutation ($input: CreateTestCaseAndTemplateMatchByNameInput!) {
            testCase {
                createWithTemplateMatchByName(input: $input) {
                testCases {
                    id, name
                }
                }
            }
            }
            """
        )

        test_case_data = []
        for test_case in test_cases:
            test_case_data.append({
                "testCaseData": dict(test_case)
            })

        test_case_vars = {
            "input": {
                "db": db,
                "campaignId": campaign_id,
                "createTestCaseInputs": test_case_data
            }
        }

        test_case_created_response = { "testcases": [] }

        result = client.execute(test_case_mutation, variable_values=test_case_vars)

        if "testCase" in result.keys():
            test_case_type_res = result["testCase"]
            if "createWithTemplateMatchByName" in test_case_type_res:
                create_res = test_case_type_res["createWithTemplateMatchByName"]
                if "testCases" in create_res:
                    test_cases_created = create_res["testCases"]

                    for test_case in test_cases_created:
                        test_case_created_response['testcases'].append({"id": test_case["id"], "name": test_case["name"]})
    except Exception as e:
        return 500, f"Error creating test cases: {e}"

    return 200, test_case_created_response


def get_org_id_for_campaign_and_assessment_data(connection_params: VectrGQLConnParams, org_name: str) -> str:
    client = get_client(connection_params)

    org_query = gql(
        """
        query($nameVar: String) {
          organizations(filter: {name: {eq:  $nameVar}}) {
            nodes {
              id, name
            }
          }
        }
    """
    )

    org_vars = {"nameVar": org_name}

    result = client.execute(org_query, variable_values=org_vars)

    if "organizations" in result.keys():
        organizations_type_res = result["organizations"]
        if "nodes" in organizations_type_res:
            nodes_res = organizations_type_res["nodes"]
            if nodes_res:
                return nodes_res[0]["id"]

    raise RuntimeError("couldn't find org name. create in VECTR first")


def get_assessment_by_name(connection_params: VectrGQLConnParams, db_name: str, assessment_name: str) -> str:
    client = get_client(connection_params)

    org_query = gql(
        """
        query ($db: String!, $nameVar: String){
          assessments(db:$db, filter: {name: {eq:  $nameVar}}) {
            nodes {
              id, name
            }
          }
        }
    """
    )
    ass_vars = {"nameVar": assessment_name, "db": db_name}
    result = client.execute(org_query, variable_values=ass_vars)
    if "assessments" in result.keys():
        assessments_type_res = result["assessments"]
        if "nodes" in assessments_type_res:
            nodes_res = assessments_type_res["nodes"]
            if nodes_res:
                return nodes_res[0]["id"]

    raise RuntimeError("couldn't find assessment name. create in VECTR first")

def get_campaign_by_name(connection_params: VectrGQLConnParams, db_name: str, campaign_name: str) -> str:
    client = get_client(connection_params)

    org_query = gql(
        """
        query ($db: String!, $nameVar: String){
          campaigns(db:$db, filter: {name: {eq:  $nameVar}}) {
            nodes {
              id, name
            }
          }
        }
    """
    )

    cpg_vars = {"nameVar": campaign_name, "db": db_name}
    result = client.execute(org_query, variable_values=cpg_vars)
    if "campaigns" in result.keys():
        campaigns_type_res = result["campaigns"]
        if "nodes" in campaigns_type_res:
            nodes_res = campaigns_type_res["nodes"]
            if nodes_res:
                return 200, nodes_res[0]["id"]

    return 500, "Couldn't find campaign name. Create it in VECTR first."

def get_testcases_for_campaign_by_id(connection_params: VectrGQLConnParams, db_name: str, campaign_id: str) -> str:
    client = get_client(connection_params)

    org_query = gql(
        """
        query ($db: String!, $idVar: String!){
          campaign(id:$idVar, db:$db) {
            id, 
            name, 
            testCases {
              id, 
              name,
              description, 
              method, 
              mitreId, 
              outcome {
              	path,
                abbreviation
              },
              outcomeNotes, 
              tags {
                name
              },
              executionArtifactIdInfo {
              	id
              },
              status, 
              attackStart {
                id, 
                createTime,
                updateTime,
                team                
              }, 
              attackStop {
                id, 
                createTime,
                updateTime,
                team
              }
            }
          }
        }
        """
    )

    cpg_vars = {"idVar": campaign_id, "db": db_name}
    result = client.execute(org_query, variable_values=cpg_vars)
    if "campaign" in result.keys():
        campaign_type_res = result["campaign"]
        if "testCases" in campaign_type_res:
            return 200, campaign_type_res["testCases"]

    return 500, "Couldn't find campaign name. Create it in VECTR first."


def transform_mythic_task_to_testcase(vectr_con, task_data, provided_test_case_name, override_mitre_technique_id, override_mitre_tactic_name):
    task = task_data.get('task', {})
    task_metadata = task_data.get('task_metadata', {})
    callback = task_data.get('callback', {})
    responses = task_data.get('responses', [])
    
    if provided_test_case_name:
        test_case_name = provided_test_case_name
    else:
        test_case_name = f"{task.get('command_name')}{' ' + task.get('original_params') if task.get('original_params') else ''}"
    
    description = f"""#### Executed via Mythic
- **Command**: {f"{task.get('command_name')}{' ' + task.get('original_params') if task.get('original_params') else ''}"}
- **Task Description**: {task_metadata.get('description')}
- **Target User**: `{callback.get('user')}`
- **Target Host**: `{callback.get('host')}`

Metadata:
```
Callback ID: {callback.get('id')}
Payload Type: {task.get('payload_type')}
Task ID: {task.get('id')}
```
"""

    mitre_id = task_metadata.get('attack') if task_metadata.get('attack') else "T1204"
    if override_mitre_technique_id:
        mitre_id = override_mitre_technique_id.upper()

    mitre_tactic_name = override_mitre_tactic_name.title() if override_mitre_tactic_name else "Execution"

    outcome_notes = "#### Command Output\n```"
    for response in responses:
        outcome_notes += "\n" + response.get('response')
    outcome_notes += "\n```"

    tags = []
    if task.get('payload_type'):
        tags.append(task.get('payload_type'))
    if task.get('status'):
        tags.append(f"task_status:{task.get('status')}")
    if task.get('operator_username'):
        tags.append(f"mythic_user:{task.get('operator_username')}")
    if callback.get('user'):
        tags.append(f"callback_user:{callback.get('user')}")
    if callback.get('host'):
        tags.append(f"callback_host:{callback.get('host')}")
    if callback.get('display_id'):
        tags.append(f"callback_host:{callback.get('display_id')}")

    outcome = "TBD"
    
    target_hosts = []
    if callback.get('host'):
        target_hosts.append(callback.get('host'))

    execution_epoch = int(datetime.strptime(task['timestamp'][:26], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp()) * 1000
    
    return TestCase(
        Variant=f"{test_case_name}",
        Objective=description,
        Phase=mitre_tactic_name,
        MitreID=mitre_id,
        Tags=','.join(tags),
        Status="Completed",
        Outcome=outcome,
        OutcomeNotes=outcome_notes,
        TargetAssets=','.join(target_hosts),
        # ExpectedDetectionLayers="",
        # AlertTriggered="Yes" if was_detected else "No",
        # References=references,
        # DetectingTools=detecting_tools,
        # ActivityLogged=activity_logged,
        StartTimeEpoch=execution_epoch,
        StopTimeEpoch=execution_epoch,
        Organizations=vectr_con.org_name
    )

def encrypt_execution_artifact(artifact_data):
    # Generate a hash of the encoded data
    hash_hex = generichash(artifact_data, digest_size=32).decode()

    # Encrypt the data using SecretBox
    key = nacl.utils.random(SecretBox.KEY_SIZE)
    nonce = nacl.utils.random(SecretBox.NONCE_SIZE)
    box = SecretBox(key)
    encrypted = box.encrypt(artifact_data, nonce)

    # Encode the encrypted data and nonce in base64
    encrypted_base64 = Base64Encoder.encode(encrypted.ciphertext).decode()
    key_base64 = Base64Encoder.encode(key).decode()
    nonce_base64 = Base64Encoder.encode(nonce).decode()
    
    return encrypted_base64, key_base64, nonce_base64, hash_hex


async def process_standard_response(response_code: int, response_data: any,
                                    taskData: PTTaskMessageAllData, response: PTTaskCreateTaskingMessageResponse, as_json=True) -> \
        PTTaskCreateTaskingMessageResponse:
    if response_code == 200:
        await SendMythicRPCResponseCreate(MythicRPCResponseCreateMessage(
            TaskID=taskData.Task.ID,
            Response=json.dumps(response_data).encode("UTF8") if as_json else f"{response_data}".encode("UTF8"),
        ))
        response.Success = True
    else:
        await SendMythicRPCResponseCreate(MythicRPCResponseCreateMessage(
            TaskID=taskData.Task.ID,
            Response=f"{response_data}".encode("UTF8"),
        ))
        response.TaskStatus = "Error: VECTR API Error"
        response.Success = False
    return response