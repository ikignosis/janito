"""
Clear Statement Format Parser Implementation
Version: 2.4.3
"""

class Container:
    """Base class for Document, Scope, and Statement containers"""
    def __init__(self, name="root"):
        self.name = name
        self.literal = []  # Literal block lines
        self.slist = []    # Simple list items
        self.kv = {}       # Key-value pairs
        self.scopes = []   # Child scopes
        self.statements = [] # Child statements
        
    def add_literal(self, content):
        """Add a literal line (without the leading dot)"""
        self.literal.append(content)
        
    def add_list_item(self, item):
        """Add a list item (without the leading dash)"""
        self.slist.append(item.strip())
        
    def add_kv(self, key, value):
        """Add a key-value pair"""
        if value and isinstance(value, str):
            self.kv[key.strip()] = value.strip()
        else:
            self.kv[key.strip()] = value if value else ""
        
    def add_scope(self, scope):
        """Add a child scope"""
        self.scopes.append(scope)
        
    def add_statement(self, statement):
        """Add a child statement"""
        self.statements.append(statement)

class Document(Container):
    """Root container for the entire document"""
    pass

class Scope(Container):
    """Named container that can hold other elements"""
    pass

class Statement(Container):
    """Named action or configuration container"""
    pass

class Parser:
    def __init__(self):
        self.document = Document()
        self.container_stack = [self.document]  # Stack of current containers
        self.orphan_key = None  # Track key without value for multiline content
        
    @property
    def current_container(self):
        """Get the current container from top of stack"""
        return self.container_stack[-1]
    
    def parse(self, content):
        """Parse the given content string"""
        # Normalize line endings and split into lines
        lines = content.replace('\r\n', '\n').split('\n')
        
        for line in lines:
            line = line.rstrip()  # Remove trailing whitespace
            
            # Skip empty lines and comments
            if not line or line.lstrip().startswith('#'):
                continue
                
            self.parse_line(line)
            
        return self.document
    
    def parse_line(self, line):
        """Parse a single line of content"""
        stripped = line.lstrip()  # Remove leading whitespace
        
        if stripped.startswith('.'):  # Literal line
            self.handle_literal_line(stripped[1:])
        elif stripped.startswith('-'):  # List item
            self.handle_list_item(stripped[1:])
        elif stripped.startswith('/'):  # Scope marker
            name = stripped[1:].strip()
            self.handle_scope_marker(name)
        elif ':' in stripped:  # Key-value pair
            self.handle_key_value(stripped)
        else:  # Statement
            self.handle_statement(stripped)
    
    def handle_literal_line(self, content):
        """Handle a literal line (starts with .)"""
        if self.orphan_key:
            # Add to the orphan key's value
            current_value = self.current_container.kv.get(self.orphan_key, "")
            if current_value:
                current_value += "\n"
            current_value += content
            self.current_container.kv[self.orphan_key] = current_value
        else:
            # Add to container's literal property
            self.current_container.add_literal(content)
    
    def handle_list_item(self, content):
        """Handle a list item (starts with -)"""
        content = content.strip()
        print(f"Debug - List item: '{content}' (orphan_key: {self.orphan_key}) in container: {self.current_container.name}")
        if self.orphan_key:
            # Convert orphan key value to list if needed
            key = self.orphan_key
            if not isinstance(self.current_container.kv.get(key), list):
                self.current_container.kv[key] = []
            self.current_container.kv[key].append(content)
            print(f"Debug - Added to key '{key}': {self.current_container.kv[key]}")
        else:
            # Add to container's slist property
            self.current_container.add_list_item(content)
    
    def handle_scope_marker(self, name):
        """Handle a scope marker (starts with /)"""
        name = name.strip()
        
        if not name:  # Scope end marker
            while len(self.container_stack) > 1:  # Don't pop the root document
                popped = self.container_stack.pop()
                print(f"Debug - Popped container: {popped.name}")
                # Stop if we popped a Scope
                if isinstance(popped, Scope):
                    break
            self.orphan_key = None
        else:  # Scope start
            # Make sure we're in a valid container for the new scope
            while isinstance(self.current_container, Statement):
                print(f"Debug - Popping statement before new scope: {self.current_container.name}")
                self.container_stack.pop()
                
            print(f"Debug - Creating new scope '{name}' in container: {self.current_container.name}")
            new_scope = Scope(name)
            self.current_container.add_scope(new_scope)
            self.container_stack.append(new_scope)
            self.orphan_key = None
    
    def handle_key_value(self, line):
        """Handle a key-value pair (contains :)"""
        key, value = [part.strip() for part in line.split(':', 1)]
        
        if value:  # Inline value
            self.current_container.add_kv(key, value)
            self.orphan_key = None
        else:  # No inline value - mark as orphan key for multiline
            self.current_container.add_kv(key, "")
            self.orphan_key = key
    
    def handle_statement(self, content):
        """Handle a statement (plain text)"""
        # Pop back to the appropriate container level
        while isinstance(self.current_container, Statement):
            print(f"Debug - Popping out of statement: {self.current_container.name}")
            self.container_stack.pop()
            
        # Create the new statement
        new_statement = Statement(content.strip())
        print(f"Debug - Creating new statement: {new_statement.name} in container: {self.current_container.name}")
        
        # Add to current container and push onto stack
        self.current_container.add_statement(new_statement)
        self.container_stack.append(new_statement)
        self.orphan_key = None

def test_parser():
    """Test the parser implementation"""
    test_content = """version: 1.0
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
    /"""

    parser = Parser()
    doc = parser.parse(test_content)
    
    # Test document level properties
    assert doc.kv["version"] == "1.0"
    assert doc.kv["environment"] == "production"
    assert doc.kv["startup_script"] == "#!/bin/bash\necho \"Starting...\""
    assert set(doc.kv["allowed_ports"]) == {"80", "443"}
    
    # Test root scopes
    system_settings = doc.scopes[0]
    assert system_settings.name == "System Settings"
    assert system_settings.kv["timezone"] == "UTC"
    assert system_settings.kv["locale"] == "en_US.UTF-8"
    
    # Test nested statements and their KV pairs
    nginx_service = system_settings.statements[0]
    assert nginx_service.name == "Configure Service"
    assert nginx_service.kv["name"] == "nginx"
    assert nginx_service.kv["state"] == "enabled"
    
    docker_service = system_settings.statements[1]
    assert docker_service.name == "Configure Service"
    assert docker_service.kv["name"] == "docker"
    assert docker_service.kv["state"] == "enabled"
    
    # Test nested scopes
    print("Debug - system_settings scopes:", [scope.name for scope in system_settings.scopes])
    print("Debug - system_settings statements:", [stmt.name for stmt in system_settings.statements])
    
    # Find Security scope (should be first scope after Configure Service statements)
    statements_before_security = [s for s in system_settings.statements if s.name == "Configure Service"]
    security = system_settings.scopes[0]  # Security should be the first scope
    assert security.name == "Security", f"Expected 'Security', got '{security.name}' (scopes: {[s.name for s in system_settings.scopes]})"
    assert security.kv.get("rules") is not None, f"No rules found in security scope {security.name}"
    assert "disable root login" in security.kv["rules"]
    assert "enforce password policy" in security.kv["rules"]
    
    # Test document level statements
    users = [s for s in doc.statements if s.name == "Configure User"]
    assert len(users) == 2
    assert users[0].kv["username"] == "admin"
    assert "sudo" in users[0].kv["groups"]
    assert users[1].kv["username"] == "deploy"
    assert "deploy" in users[1].kv["groups"]
    
    print("All tests passed!")

if __name__ == "__main__":
    test_parser()