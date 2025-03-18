import subprocess
import os
import platform
import time
import uuid
import sys
import io
import codecs

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
        
        # Configure UTF-8 support for Windows
        if platform.system() == "Windows":
            # Force UTF-8 mode in Python 3.7+
            os.environ["PYTHONUTF8"] = "1"
            
            # Set Python's standard IO encoding to UTF-8
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8')
            if hasattr(sys.stdin, 'reconfigure'):
                sys.stdin.reconfigure(encoding='utf-8')
                
            # Ensure Windows console is in UTF-8 mode
            try:
                # Try to set console mode to UTF-8
                os.system("chcp 65001 > nul")
                
                # Redirect stdout through a UTF-8 writer
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
            except Exception as e:
                print(f"Warning: Failed to set up UTF-8 encoding: {str(e)}")
        
        # If bash_path is not provided, try to detect it
        if self.bash_path is None:
            if platform.system() == "Windows":
                # Common paths for Git Bash on Windows
                possible_paths = [
                    r"C:\Program Files\Git\bin\bash.exe",
                    r"C:\Program Files (x86)\Git\bin\bash.exe",
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        self.bash_path = path
                        break
                if self.bash_path is None:
                    raise FileNotFoundError("Could not find Git Bash executable. Please specify the path manually.")
            else:
                # On Unix-like systems, bash is usually in the PATH
                self.bash_path = "bash"
        
        # Start the bash process
        self.start_process()
    
    def start_process(self):
        """Start the Bash process."""
        # Create a subprocess with pipe for stdin, stdout, and stderr
        bash_args = [self.bash_path]
        
        # Set UTF-8 codepage for Windows
        env = os.environ.copy()
        if platform.system() == "Windows":
            # Set codepage to UTF-8 (65001) - run this before starting the process
            os.system("chcp 65001 > nul")
            # Set environment variables for proper UTF-8 handling
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            # Add additional environment variables for Windows CMD
            env["LANG"] = "en_US.UTF-8"
            env["LC_ALL"] = "en_US.UTF-8"
        
        # Create the process with binary pipes for better control over encoding
        if platform.system() == "Windows":
            # On Windows, we need special handling for UTF-8
            self.process = subprocess.Popen(
                bash_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                bufsize=0,                # Unbuffered
                universal_newlines=False, # Use binary mode
                env=env                   # Pass the modified environment
            )
            
            # Create UTF-8 wrappers for stdin/stdout
            self.stdin = io.TextIOWrapper(self.process.stdin, encoding='utf-8', errors='replace', line_buffering=True)
            self.stdout = io.TextIOWrapper(self.process.stdout, encoding='utf-8', errors='replace', line_buffering=True)
        else:
            # On Unix systems, the standard approach works fine
            self.process = subprocess.Popen(
                bash_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                text=True,                # Use text mode for input/output
                bufsize=0,                # Unbuffered
                universal_newlines=True,  # Universal newlines mode
                env=env,                  # Pass the modified environment
                encoding='utf-8',         # Explicitly set encoding to UTF-8
                errors='replace'          # Replace invalid characters instead of failing
            )
            self.stdin = self.process.stdin
            self.stdout = self.process.stdout
        
        # Set up a more reliable environment
        setup_commands = [
            "export PS1='$ '",  # Simple prompt to avoid parsing issues
            "export TERM=dumb",  # Disable color codes and other terminal features
            "set +o history",  # Disable history
            "shopt -s expand_aliases", # Enable alias expansion
            "export LANG=en_US.UTF-8", # Set UTF-8 locale
            "export LC_ALL=en_US.UTF-8", # Set all locale categories to UTF-8
        ]
        
        # Additional setup for Windows to handle UTF-8
        if platform.system() == "Windows":
            setup_commands.extend([
                # Force Git Bash to use UTF-8
                "export LESSCHARSET=utf-8",
                # Ensure proper display of Unicode characters
                "export PYTHONIOENCODING=utf-8"
            ])
        
        # Send setup commands
        for cmd in setup_commands:
            self._send_command(cmd)
        
        # Clear initial output with a marker
        marker = f"INIT_COMPLETE_{uuid.uuid4().hex}"
        self._send_command(f"echo {marker}")
        
        while True:
            line = self.stdout.readline().strip()
            if marker in line:
                break
    
    def _send_command(self, command):
        """Send a command to the Bash process without reading the output."""
        if self.process is None or self.process.poll() is not None:
            self.start_process()
            
        # Use our stdin wrapper instead of process.stdin directly
        self.stdin.write(command + "\n")
        self.stdin.flush()
    
    def execute(self, command, timeout=None):
        """
        Execute a command in the Bash session and return the output.
        
        Args:
            command (str): The command to execute.
            timeout (int, optional): Timeout in seconds. If None, no timeout is applied.
            
        Returns:
            str: The command output.
        """
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
                    line = self.stdout.readline().strip()
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
                wrapped_command = f"timeout {timeout}s bash -c \"{command.replace('"', '\\"')}\" 2>&1; echo '{end_marker}'"
            else:
                wrapped_command = f"{command} 2>&1; echo '{end_marker}'"
        else:
            wrapped_command = f"{command} 2>&1; echo '{end_marker}'"
        
        # Send the command
        self._send_command(wrapped_command)
        
        # Import the console here to avoid circular imports
        from janito.tools.rich_console import console
        
        # Collect output until the end marker is found
        output_lines = []
        start_time = time.time()
        max_wait = timeout if timeout is not None else 3600  # Default to 1 hour if no timeout
        
        while time.time() - start_time < max_wait + 5:  # Add buffer time
            try:
                line = self.stdout.readline().rstrip('\r\n')
                if end_marker in line:
                    break
                    
                # Print the output to the console in real-time
                if line:
                    console.print(line)
                    
                output_lines.append(line)
            except UnicodeDecodeError as e:
                # Handle potential UTF-8 decoding errors
                error_msg = f"[Warning: Unicode decode error occurred: {str(e)}]"
                console.print(error_msg, style="yellow")
                output_lines.append(error_msg)
                # Just continue with replacement character
                continue
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
    
    def windows_to_bash_path(self, windows_path):
        """
        Convert a Windows path to a Git Bash compatible path.
        
        Args:
            windows_path (str): A Windows path like 'C:\\folder\\file.txt'
            
        Returns:
            str: Git Bash compatible path like '/c/folder/file.txt'
        """
        if not windows_path or not platform.system() == "Windows":
            return windows_path
            
        # Handle drive letter (e.g., C: -> /c)
        if ":" in windows_path:
            drive, path = windows_path.split(":", 1)
            unix_path = f"/{drive.lower()}{path}"
        else:
            unix_path = windows_path
            
        # Convert backslashes to forward slashes
        unix_path = unix_path.replace("\\", "/")
        
        # Remove any double slashes
        while "//" in unix_path:
            unix_path = unix_path.replace("//", "/")
            
        # If the path contains spaces, we need to escape them or quote the entire path
        if " " in unix_path:
            unix_path = f'"{unix_path}"'
            
        return unix_path
    
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