

function get_date_time_string() {
    var currentdate = new Date(); 
    var datetime = currentdate.getDate() + "/"
    + (currentdate.getMonth()+1)  + "/" 
    + currentdate.getFullYear() + " @ "  
    + currentdate.getHours() + ":"  
    + currentdate.getMinutes() + ":" 
    + currentdate.getSeconds();
    return datetime;
}

async function query_server(url, dict_obj, handle_server_response, error_callback) {
    let response = await fetch(url, {
        method: "POST",
        headers: { "Content-type": "application/json" },
        body: JSON.stringify(dict_obj)
        }).catch(e => {
            // console.log(e);
            if (error_callback) error_callback()
        });

    // only call text() if the first promise succeeded. TODO figure out how to chain these
    if (response) {
        let data = await response.text().catch(e => {
            // dont do anything
        });
        
        // console.log(data);
        if (handle_server_response) {
            handle_server_response(JSON.parse(data))
        }
    }

}

