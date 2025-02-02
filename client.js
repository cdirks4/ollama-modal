async function generateText(prompt) {
  try {
    const response = await fetch("https://your-modal-endpoint/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text: prompt }),
    });

    const data = await response.json();
    return data.responses;
  } catch (error) {
    console.error("Error:", error);
    throw error;
  }
}

// Example usage:
generateText("Write a Python function to calculate fibonacci numbers")
  .then((responses) => {
    responses.forEach((response, index) => {
      console.log(`Response from GPU ${index + 1}:`, response);
    });
  })
  .catch((error) => {
    console.error("Error:", error);
  });
