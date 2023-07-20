import os.path
import json
from http.server import BaseHTTPRequestHandler, HTTPServer



class HTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, on_post=None, root_dir='root', default_index="index.html", **kwargs):
        self._on_post = on_post
        self._root_dir = root_dir
        self._default_index = default_index
        self._file_type_to_header_type = {'.html':'text/html', 
                                          '.ico':'image/x-icon',
                                          '.jpg':'image/jpeg',
                                          '.css':'text/css',
                                          '.js':'text/javascript'}
                                          
        super().__init__(*args, **kwargs)

    def do_POST(self):
        if self._on_post:
            self._on_post(self)

    def _send_file(self, file_path):

        # get the ".html" or ".ico", etc
        file_type = os.path.splitext(file_path)[1]
        content_type = self._file_type_to_header_type[file_type] if file_type in self._file_type_to_header_type else 'Not Found'
        status = 200

        if file_type not in self._file_type_to_header_type:
            print('sorry, i dont recognize the desired file type and consequently dont know what to set the html contet type to. maybe we wouldnt have this problem if i didnt try rolling my own webserver')

        # check if file exists
        if not os.path.exists(file_path):
            file_path = os.path.join(self._root_dir, "404.html")
            content_type = 'Not Found'
            status = 404

        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()

        # send desired file
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
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
        self._send_file(file_path, )
