function(task, responses){
    function getOutcomeColour(text){
        switch (text) {
            case "High":
                return {"backgroundColor": "rgb(251, 139, 138)"}
            case "Med":
                return {"backgroundColor": "rgb(242, 183, 145)"}
            case "Low":
                return {"backgroundColor": "rgb(177, 213, 154)"}
            case "Info":
                return {"backgroundColor": "rgb(153, 153, 153)"}
            default:
                return {}
        }
    }

    if(task.status.includes("error")){
        const combined = responses.reduce( (prev, cur) => {
            return prev + cur;
        }, "");
        return {'plaintext': combined};
    }else if(task.completed){
        if(responses.length > 0){
            try{
                let data = JSON.parse(responses[0]);
                let output_table = [];
                for(let i = 0; i < data.length; i++){
                    let outcomeText = "";
                    let cellStyle = {};
                    if(data[i]["outcome"]["path"] == "TBD"){
                        outcomeText = "TBD";
                    } else if (data[i]["outcome"]['path'].startsWith("Alerted")) {
                        outcomeText = `Alerted (${data[i]["outcome"]['abbreviation']})`;
                        cellStyle = getOutcomeColour(data[i]["outcome"]['abbreviation']);
                    } else if (data[i]["outcome"]['path'].startsWith("Blocked")) {
                        if (data[i]["outcome"]['abbreviation'] == "Blocked") {
                            outcomeText = `Blocked`;
                        } else {
                            outcomeText = `Blocked (${data[i]["outcome"]['abbreviation']})`;
                        }
                        cellStyle = getOutcomeColour("High");
                    } else if (data[i]["outcome"]['path'].startsWith("Logged")) {
                        outcomeText = `Logged (${data[i]["outcome"]['abbreviation']})`;
                        cellStyle = getOutcomeColour("Info");
                    } else {
                        outcomeText = ""
                        cellStyle = {}
                    }
                    let execution_time = ""
                    if (data[i]["attackStart"] != null) {
                        execution_time = new Date(data[i]["attackStart"]["createTime"]).toString()
                    }

                    let execution_artifact_count = "0"
                    if (data[i]["executionArtifactIdInfo"] != null) {
                        execution_artifact_count = data[i]["executionArtifactIdInfo"].length.toString()
                    }

                    output_table.push({
                        "id": {"plaintext": data[i]["id"], "copyIcon": true },
                        "timestamp": {"plaintext": execution_time},
                        "name": {"plaintext": data[i]["name"]},
                        "method": {"plaintext":  data[i]["method"]},
                        "mitreId": {"plaintext":  data[i]["mitreId"]},
                        "EA": {"plaintext":  execution_artifact_count, "startIcon": "upload", "startIconHoverText":"Execution Artifacts"},
                        "tags": {
                            "button": {
                                "name": data[i]["tags"].length.toString(), 
                                "type": "string",
                                "value": data[i]["tags"].map(tag => tag.name).join("\n"),
                                "title": "Tags",
                                "startIcon": "list",
                                "hoverText": "View tags"
                            }
                        },
                        "notes": {
                            "button": {
                                "name": "", 
                                "type": "string",
                                "value": data[i]["operatorGuidance"],
                                "disabled": data[i]["operatorGuidance"] == null || data[i]["operatorGuidance"] == "",
                                "title": "Notes",
                                "startIcon": "list",
                                "hoverText": "View operator guidance"
                            }
                        },
                        "desc": {
                            "button": {
                                "name": "",
                                "type": "string",
                                "value": data[i]["description"],
                                "disabled": data[i]["description"] == null || data[i]["description"] == "",
                                "title": "Description",
                                "startIcon": "list",
                                "hoverText": "View full description"
                            }
                        },
                        "outcomeNotes": {
                            "button": {
                                "name": "",
                                "type": "string",
                                "value": data[i]["outcomeNotes"],
                                "disabled": data[i]["outcomeNotes"] == null || data[i]["outcomeNotes"] == "",
                                "title": "Outcome Notes",
                                "startIcon": "list",
                                "hoverText": "View outcome notes"
                            }
                        },
                        "status": {"plaintext":  data[i]["status"]},
                        "outcome": {"plaintext":  outcomeText, "cellStyle": cellStyle},
                        "actions": {
                            "button": {
                                "name": "Actions",
                                "type": "menu",
                                "value": [
                                    {
                                        "name": "Update Notes",
                                        "type": "task",
                                        "ui_feature": "vectr:testcase_opguidance_update",
                                        "parameters": {
                                            "test_case_id": data[i]["id"] + " - " + data[i]["name"],
                                            "content": data[i]["operatorGuidance"]
                                        },
                                        "openDialog": true
                                    },
                                    {
                                        "name": "Update Test Case Name",
                                        "type": "task",
                                        "ui_feature": "vectr:testcase_name_update",
                                        "parameters": {
                                            "test_case_id": data[i]["id"] + " - " + data[i]["name"],
                                            "name": data[i]["name"]
                                        },
                                        "openDialog": true
                                    },
                                    {
                                        "name": "Update Test Case MITRE ATT&CK",
                                        "type": "task",
                                        "ui_feature": "vectr:testcase_mitre_update",
                                        "parameters": {
                                            "test_case_id": data[i]["id"] + " - " + data[i]["name"]
                                        },
                                        "openDialog": true
                                    },
                                    {
                                        "name": "Upload Execution Artifact",
                                        "type": "task",
                                        "ui_feature": "vectr:testcase_artifact_upload",
                                        "parameters": {
                                            "test_case_id": data[i]["id"] + " - " + data[i]["name"]
                                        },
                                        "openDialog": true
                                    },
                                    {
                                        "name": "Delete Test Case",
                                        "type": "task",
                                        "ui_feature": "vectr:testcase_delete",
                                        "parameters": data[i]["id"],
                                        "getConfirmation": true
                                    },
                                    {
                                        "name": "Get Test Case JSON",
                                        "type": "task",
                                        "ui_feature": "vectr:testcase_get_raw",
                                        "parameters": data[i]["id"]
                                    },
                                ]
                            }
                        },
                    });
                }
                return {
                    "table": [
                        {
                            "headers": [
                                {"plaintext": "id", "type": "string", "width": 100},
                                {"plaintext": "timestamp", "type": "string", "width": 285},
                                {"plaintext": "name", "type": "string", "fillWidth": true},
                                {"plaintext": "method", "type": "string", "fillWidth": true},
                                {"plaintext": "mitreId", "type": "string", "width": 100},
                                {"plaintext": "EA", "type": "string", "width": 50, "disableSort": true},
                                {"plaintext": "tags", "type": "button", "width": 70, "disableSort": true},
                                {"plaintext": "notes", "type": "button", "width": 70, "disableSort": true},
                                {"plaintext": "desc", "type": "button", "cellStyle": {}, "width": 70, "disableSort": true},
                                {"plaintext": "outcomeNotes", "type": "button", "cellStyle": {}, "width": 150, "disableSort": true},
                                {"plaintext": "status", "type": "string", "width": 125},
                                {"plaintext": "outcome", "type": "string", "width": 200},
                                {"plaintext": "actions", "type": "button", "width": 90, "disableSort": true},
                            ],
                            "rows": output_table,
                            "title": "Test Cases"
                        }
                    ]
                }
            }catch(error){
                console.log(error);
                const combined = responses.reduce( (prev, cur) => {
                    return prev + cur;
                }, "");
                return {'plaintext': combined};
            }
        }else{
            return {"plaintext": "No output from command"};
        }
    }else{
        return {"plaintext": "No data to display..."};
    }
}
