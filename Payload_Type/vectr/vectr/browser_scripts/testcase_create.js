function(task, responses){
    if(task.status.includes("error")){
        const combined = responses.reduce( (prev, cur) => {
            return prev + cur;
        }, "");
        return {'plaintext': combined};
    }else if(task.completed){
        if(responses.length > 0){
            try{
                let response_data = JSON.parse(responses[0]);
                let data = response_data["testcases"];
                let output_table = [];
                for(let i = 0; i < data.length; i++){
                    output_table.push({
                        "id": {"plaintext": data[i]["id"], "copyIcon": true },
                        "name": {"plaintext": data[i]["name"]},
                    });
                }
                return {
                    "table": [
                        {
                            "headers": [
                                {"plaintext": "id", "type": "string", "width": 100},
                                {"plaintext": "name", "type": "string", "fillWidth": true},
                            ],
                            "rows": output_table,
                            "title": "Created Test Case"
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