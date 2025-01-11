class ClearParser:
    def __init__(self):
        self.document = {
            "kv": {},       # Key/Value pairs
            "slist": [],    # List items
            "literal": "",  # Literal content
            "scopes": [],   # Scopes
            "statements": []  # Statements
        }
        self.current_container = self.document
        self.container_stack = [self.document]

    def parse(self, text):
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # Skip empty lines and comments
            self._parse_line(line)

    def _parse_line(self, line):
        if line.startswith("."):
            self._parse_literal(line)
        elif line.startswith("-"):
            self._parse_list_item(line)
        elif line.startswith("/"):
            self._parse_scope(line)
        elif ":" in line:
            self._parse_key_value(line)
        else:
            self._parse_statement(line)

    def _parse_literal(self, line):
        content = line[1:].rstrip()
        if "literal" not in self.current_container:
            self.current_container["literal"] = ""
        self.current_container["literal"] += content + "\n"

    def _parse_list_item(self, line):
        content = line[1:].strip()
        if "slist" not in self.current_container:
            self.current_container["slist"] = []
        self.current_container["slist"].append(content)

    def _parse_scope(self, line):
        if line == "/":
            # End of scope
            self.container_stack.pop()
            self.current_container = self.container_stack[-1]
        else:
            # Start of scope
            scope_name = line[1:].strip()
            new_scope = {
                "name": scope_name,
                "kv": {},
                "slist": [],
                "literal": "",
                "scopes": [],
                "statements": []
            }
            if "scopes" not in self.current_container:
                self.current_container["scopes"] = []
            self.current_container["scopes"].append(new_scope)
            self.container_stack.append(new_scope)
            self.current_container = new_scope

    def _parse_key_value(self, line):
        key, value = map(str.strip, line.split(":", 1))
        if not value:
            # Multiline value (list or literal)
            self.current_container["kv"][key] = None
        else:
            # Single-line value
            self.current_container["kv"][key] = value

    def _parse_statement(self, line):
        statement_name = line.strip()
        new_statement = {
            "name": statement_name,
            "kv": {},
            "slist": [],
            "literal": "",
            "scopes": [],
            "statements": []
        }
        if "statements" not in self.current_container:
            self.current_container["statements"] = []
        self.current_container["statements"].append(new_statement)
        self.container_stack.append(new_statement)
        self.current_container = new_statement

    def get_parsed_data(self):
        return self.document


def test_parser():
    input_text = """
    version: 1.0
    environment: production
    allowed_ports:
    - 80
    - 443
    startup_script:
    .#!/bin/bash
    .echo "Starting..."

    /System Settings
        timezone: UTC
        locale: en_US.UTF-8
        
        Configure Service
            name: nginx
            state: enabled
        
        Configure Service
            name: docker
            state: enabled
        
        /Security
            rules:
            - disable root login
            - enforce password policy
        /
    /

    /Network Settings
        interface: eth0
        
        Configure IP
            address: 192.168.1.100
            netmask: 255.255.255.0
        
        /Firewall
            rules:
            - allow 80/tcp
            - allow 443/tcp
        /
    /

    Configure User
        username: admin
        shell: /bin/bash
        groups:
        - sudo
        - docker

    Configure User
        username: deploy
        shell: /bin/bash
        groups:
        - deploy
        - docker

    Install Dependencies
        packages:
        - nginx
        - openssl
        
        /Post Install
            - enable nginx
            - start nginx
        /
    """

    parser = ClearParser()
    parser.parse(input_text)
    parsed_data = parser.get_parsed_data()

    # Assertions to verify correctness
    assert parsed_data["kv"]["version"] == "1.0"
    assert parsed_data["kv"]["environment"] == "production"
    assert parsed_data["slist"] == ["80", "443"]
    assert parsed_data["literal"].strip() == "#!/bin/bash\necho \"Starting...\""

    system_settings = parsed_data["scopes"][0]
    assert system_settings["name"] == "System Settings"
    assert system_settings["kv"]["timezone"] == "UTC"
    assert system_settings["kv"]["locale"] == "en_US.UTF-8"

    nginx_service = system_settings["statements"][0]
    assert nginx_service["name"] == "Configure Service"
    assert nginx_service["kv"]["name"] == "nginx"
    assert nginx_service["kv"]["state"] == "enabled"

    security_scope = system_settings["scopes"][0]
    assert security_scope["name"] == "Security"
    assert security_scope["slist"] == ["disable root login", "enforce password policy"]

    network_settings = parsed_data["scopes"][1]
    assert network_settings["name"] == "Network Settings"
    assert network_settings["kv"]["interface"] == "eth0"

    configure_ip = network_settings["statements"][0]
    assert configure_ip["name"] == "Configure IP"
    assert configure_ip["kv"]["address"] == "192.168.1.100"
    assert configure_ip["kv"]["netmask"] == "255.255.255.0"

    firewall_scope = network_settings["scopes"][0]
    assert firewall_scope["name"] == "Firewall"
    assert firewall_scope["slist"] == ["allow 80/tcp", "allow 443/tcp"]

    configure_user_admin = parsed_data["statements"][0]
    assert configure_user_admin["name"] == "Configure User"
    assert configure_user_admin["kv"]["username"] == "admin"
    assert configure_user_admin["kv"]["shell"] == "/bin/bash"
    assert configure_user_admin["slist"] == ["sudo", "docker"]

    configure_user_deploy = parsed_data["statements"][1]
    assert configure_user_deploy["name"] == "Configure User"
    assert configure_user_deploy["kv"]["username"] == "deploy"
    assert configure_user_deploy["kv"]["shell"] == "/bin/bash"
    assert configure_user_deploy["slist"] == ["deploy", "docker"]

    install_dependencies = parsed_data["statements"][2]
    assert install_dependencies["name"] == "Install Dependencies"
    assert install_dependencies["slist"] == ["nginx", "openssl"]

    post_install_scope = install_dependencies["scopes"][0]
    assert post_install_scope["name"] == "Post Install"
    assert post_install_scope["slist"] == ["enable nginx", "start nginx"]

    print("All tests passed!")


# Run the test
if __name__ == "__main__":
    test_parser()