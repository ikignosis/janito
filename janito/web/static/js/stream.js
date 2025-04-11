export async function sendCommandStream(cmd, handleData) {
  const response = await fetch("/execute_stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input: cmd })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while(true) {
    const { done, value } = await reader.read();
    if(done) break;
    buffer += decoder.decode(value, {stream:true});

    let parts = buffer.split("\n\n");
    buffer = parts.pop();

    for(const part of parts) {
      if(part.startsWith("data: ")) {
        const jsonStr = part.slice(6).trim();
        try {
          const data = JSON.parse(jsonStr);
          handleData(data);
        } catch(e) {
          console.error("Error parsing SSE data", e, jsonStr);
        }
      }
    }
  }
}
