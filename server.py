from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi, json
import os.path
import shutil

class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, root_dir='root', default_index="index.html", **kwargs):
        self._root_dir = root_dir
        self._default_index = default_index
        self._file_type_to_header_type = {'.html':'text/html', 
                                          '.ico':'image/x-icon',
                                          '.jpg':'image/jpeg'}
                                          
        super().__init__(*args, **kwargs)

    def do_POST(self):

        # get the json sent to us
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        post_dict = json.loads(post_body)
        #print("post body: " + str(post_dict))

        # build our response dict
        response_dict = {'key':'value'}
        if 'date_time' in post_dict:
            response_dict['received_date_time'] =  post_dict['date_time']

        # send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(response_dict), "utf-8"))

    def send_file(self, file_path):

        # get the ".html" or ".ico", etc
        file_type = os.path.splitext(file_path)[1]

        with open(file_path, 'rb') as f:
            self.send_response(200)
            self.send_header("Content-type", self._file_type_to_header_type[file_type])
            self.end_headers()

            self.wfile.write(f.read())

    def do_GET(self):        

        # security check against accessing files higher in the dir
        if ".." in self.path:
            return
        
        desired_file = self.path.lstrip('/') # needed for os.path.join()
        # server index.html if no file was specified
        desired_file = self._default_index if desired_file == "" else desired_file

        # prepend root dir to desired file path
        file_path = os.path.join(self._root_dir, desired_file )

        # send response
        self.send_file(file_path, )


if __name__ == "__main__":
    if not os.path.isfile('config.py'):  # Need to create config file if it doesn't exist
        shutil.copy("config-example.py", "config.py")
    server = HTTPServer(('', 8080), Handler) # access with http://localhost:8080
    # server.serve_forever()
    while True:
        server.handle_request()
