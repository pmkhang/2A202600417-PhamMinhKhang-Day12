import { OpenAI } from "openai";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    if (!process.env.OPENAI_API_KEY) {
      return Response.json(
        { error: "OpenAI API Key not configured on server." },
        { status: 500 }
      );
    }

    const systemMessage = {
      role: "system",
      content: "You are a highly capable AI assistant. Always format your responses using professional Markdown. Use headings, bold text, lists, tables, and code blocks where they enhance clarity. Provide concise yet comprehensive answers.",
    };

    const response = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [systemMessage, ...messages],
    });

    return Response.json({ message: response.choices[0].message });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "An error occurred during your request.";
    console.error("OpenAI Error:", error);
    return Response.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}
