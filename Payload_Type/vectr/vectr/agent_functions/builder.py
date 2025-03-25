from mythic_container.PayloadBuilder import *
from mythic_container.MythicCommandBase import *
from mythic_container.MythicRPC import *

from vectr.VectrRequests import VectrAPI

class Vectr(PayloadType):
    name = "vectr"
    file_extension = ""
    author = "@ajpc500"
    supported_os = [
        SupportedOS("vectr")
    ]
    wrapper = False
    wrapped_payloads = []
    note = """
    This payload communicates with an existing Vectr instance. In your settings, add your Vectr API key as a secret with the key "VECTR_API_KEY".
    """
    supports_dynamic_loading = False
    mythic_encrypts = True
    translation_container = None
    agent_type = "service"
    agent_path = pathlib.Path(".") / "vectr"
    agent_icon_path = agent_path / "agent_functions" / "vectr.svg"
    agent_code_path = agent_path / "agent_code"
    build_parameters = [
        BuildParameter(
            name="URL",
            description="Vectr API URL",
            parameter_type=BuildParameterType.String,
            default_value="https://vectr:8081/sra-purpletools-rest"
        ),
        BuildParameter(
            name="org_name",
            description="Vectr Organization Name",
            parameter_type=BuildParameterType.String,
            default_value="MYTHIC"
        ),
        BuildParameter(
            name="assessment_name",
            description="Vectr Assessment Name",
            parameter_type=BuildParameterType.String,
            default_value="Mythic Assessment"
        ),
        BuildParameter(
            name="campaign_name",
            description="Vectr Campaign Name",
            parameter_type=BuildParameterType.String,
            default_value="Mythic Campaign"
        ),
        BuildParameter(
            name="target_db",
            description="Vectr Target Database",
            parameter_type=BuildParameterType.String,
            default_value="MYTHIC"
        ),
    ]
    c2_profiles = []

    async def build(self) -> BuildResponse:
        # this function gets called to create an instance of your payload
        resp = BuildResponse(status=BuildStatus.Success)
        ip = "127.0.0.1"

        create_callback = await SendMythicRPCCallbackCreate(MythicRPCCallbackCreateMessage(
            PayloadUUID=self.uuid,
            C2ProfileName="",
            User="VECTR",
            Host="VECTR",
            Domain=self.get_parameter('URL'),
            Ip=ip,
            IntegrityLevel=3,
        ))
        if not create_callback.Success:
            logger.info(create_callback.Error)
        else:
            logger.info(create_callback.CallbackUUID)
            
            update_description = await SendMythicRPCCallbackUpdate(MythicRPCCallbackUpdateMessage(
                AgentCallbackUUID=create_callback.CallbackUUID,
                Description=f"A: {self.get_parameter('assessment_name')} / C: {self.get_parameter('campaign_name')}"
            ))
            if not update_description.Success:
                logger.info(update_description.Error)

        return resp
