import subprocess
import time
import uuid

class PersistentBash:
    """
    A wrapper class that maintains a persistent Bash session.
    Allows sending commands and collecting output without restarting Bash.
    """
    
    def __init__(self, bash_path=None):
        """
        Initialize a persistent Bash session.
        
        Args:
            bash_path (str, optional): Path to the Bash executable. If None, tries to detect automatically.
        """
        self.process = None
        self.bash_path = bash_path
        
        # If bash_path is not provided, try to detect it
        if self.bash_path is None:
            # On Unix-like systems, bash is usually in the PATH
            self.bash_path = "bash"
            
            # Check if bash exists
            try:
                subprocess.run(["which", "bash"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as err:
                raise FileNotFoundError("Could not find bash executable. Please specify the path manually.") from err
        
        # Start the bash process
        self.start_process()
    
    def start_process(self):
        """Start the Bash process."""
        # Create a subprocess with pipe for stdin, stdout, and stderr
        bash_args = [self.bash_path]
        
        self.process = subprocess.Popen(
            bash_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            text=True,                # Use text mode for input/output
            bufsize=0,                # Unbuffered
            universal_newlines=True,  # Universal newlines mode
        )
        
        # Set up a more reliable environment
        setup_commands = [
            "export PS1='$ '",  # Simple prompt to avoid parsing issues
            "export TERM=dumb",  # Disable color codes and other terminal features
            "set +o history",  # Disable history
            "shopt -s expand_aliases", # Enable alias expansion
        ]
        
        # Send setup commands
        for cmd in setup_commands:
            self._send_command(cmd)
        
        # Clear initial output with a marker
        marker = f"INIT_COMPLETE_{uuid.uuid4().hex}"
        self._send_command(f"echo {marker}")
        
        while True:
            line = self.process.stdout.readline().strip()
            if marker in line:
                break
    
    def _send_command(self, command):
        """Send a command to the Bash process without reading the output."""
        if self.process is None or self.process.poll() is not None:
            self.start_process()
            
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
    
    def execute(self, command, timeout=None):
        """
        Execute a command in the Bash session and return the output.
        
        Args:
            command (str): The command to execute.
            timeout (int, optional): Timeout in seconds. If None, no timeout is applied.
            
        Returns:
            str: The command output.
        """
        from janito.tools.rich_console import console
        
        if self.process is None or self.process.poll() is not None:
            # Process has terminated, restart it
            self.start_process()
        
        # Create a unique marker to identify the end of output
        end_marker = f"END_OF_COMMAND_{uuid.uuid4().hex}"
        
        # Construct the wrapped command with echo markers
        # Only use timeout when explicitly requested
        if timeout is not None and timeout > 0:
            # Check if timeout command is available
            is_timeout_available = False
            try:
                check_cmd = "command -v timeout > /dev/null 2>&1 && echo available || echo unavailable"
                self._send_command(check_cmd)
                for _ in range(10):  # Read up to 10 lines to find the result
                    line = self.process.stdout.readline().strip()
                    if "available" in line:
                        is_timeout_available = True
                        break
                    elif "unavailable" in line:
                        is_timeout_available = False
                        break
            except:
                is_timeout_available = False

            if is_timeout_available:
                # For timeout to work with shell syntax, we need to use bash -c
                escaped_command = command.replace('"', '\\"')
                wrapped_command = f"timeout {timeout}s bash -c \"{escaped_command}\" 2>&1; echo '{end_marker}'"
            else:
                wrapped_command = f"{command} 2>&1; echo '{end_marker}'"
        else:
            wrapped_command = f"{command} 2>&1; echo '{end_marker}'"
        
        # Send the command
        self._send_command(wrapped_command)
        
        # Collect output until the end marker is found
        output_lines = []
        start_time = time.time()
        max_wait = timeout if timeout is not None else 3600  # Default to 1 hour if no timeout
        
        while time.time() - start_time < max_wait + 5:  # Add buffer time
            try:
                line = self.process.stdout.readline().rstrip('\r\n')
                if end_marker in line:
                    break
                    
                # Print the output to the console in real-time if not in trust mode
                if line:
                    from janito.config import get_config
                    if not get_config().trust_mode:
                        console.print(line)
                    
                output_lines.append(line)
            except Exception as e:
                error_msg = f"[Error reading output: {str(e)}]"
                console.print(error_msg, style="red")
                output_lines.append(error_msg)
                continue
            
        # Check for timeout
        if time.time() - start_time >= max_wait + 5:
            timeout_msg = f"Error: Command timed out after {max_wait} seconds"
            console.print(timeout_msg, style="red bold")
            output_lines.append(timeout_msg)
            
            # Try to reset the bash session after a timeout
            self.close()
            self.start_process()
        
        return "\n".join(output_lines)
    
    def close(self):
        """Close the Bash session."""
        if self.process and self.process.poll() is None:
            try:
                self._send_command("exit")
                self.process.wait(timeout=2)
            except:
                pass
            finally:
                try:
                    self.process.terminate()
                except:
                    pass
                
        self.process = None
    
    def __del__(self):
        """Destructor to ensure the process is closed."""
        self.close()