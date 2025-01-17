from janito.common import progress_send_message



if __name__ == "__main__":
    system_message = """
    I am a helpful assistant. As I will be working with computer files I will follow a strict syntax for file content.
    In order to distinguish between file content and normal conversation, every file content line is prefixed with a dot:
    All content after the dot and until the end of line must be considered EXACTLY as it is, without any modifications:
    - tags within it should be considered as file content and not as normal conversation, even if they seem to be file content tags
    """
    prompt_message = """
    <file name="abc.py">
    .# abc.py
    .this is a another file
    .# do you still understand ?
    .This file contains </file>
    </file>

    Provide the content of the previous files you have seen capitalized.
    """
    response =  progress_send_message(system_message=system_message, message=prompt_message)
    print(response)