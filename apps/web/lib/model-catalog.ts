export type PublicModelRecord = {
  name: string;
  slug: string;
  category: "General" | "Reasoning" | "Coding";
  inputPrice: string;
  outputPrice: string;
  description: string;
  capabilities?: string;
};

export const publicModelCatalog: PublicModelRecord[] = [
  {
    name: "GPT-6 Astra",
    slug: "gpt-6-astra",
    category: "General",
    inputPrice: "$0.00",
    outputPrice: "$0.00",
    description: "General-purpose frontier model for broad production workloads.",
    capabilities: "Strong default choice for multi-step generation and broad reasoning tasks.",
  },
  {
    name: "GPT-5.6 Sol",
    slug: "gpt-5.6-sol",
    category: "General",
    inputPrice: "$0.00",
    outputPrice: "$0.00",
    description: "Balanced general model for everyday developer-facing inference.",
    capabilities: "Good tradeoff between latency and reasoning depth.",
  },
  {
    name: "GPT-5.6 Luna",
    slug: "gpt-5.6-luna",
    category: "General",
    inputPrice: "$5,000.00",
    outputPrice: "$5,000.00",
    description: "General model tuned for OpenAI-compatible workflows and agent loops.",
    capabilities: "Fits common SDK and coding-assistant integrations.",
  },
  {
    name: "Grok 4.6",
    slug: "grok-4.6",
    category: "General",
    inputPrice: "$0.00",
    outputPrice: "$0.00",
    description: "General conversational model with a distinct inference profile.",
    capabilities: "Useful when you want a different model family behind the same interface.",
  },
  {
    name: "DeepSeek V4 Pro",
    slug: "deepseek-v4-pro",
    category: "Reasoning",
    inputPrice: "$0.00",
    outputPrice: "$0.00",
    description: "Reasoning-oriented model for deeper analytical tasks.",
    capabilities: "Well suited to heavier technical and structured reasoning workflows.",
  },
  {
    name: "DeepSeek V4 Flash",
    slug: "deepseek-v4-flash",
    category: "Reasoning",
    inputPrice: "$0.00",
    outputPrice: "$0.00",
    description: "Faster reasoning variant for lighter latency-sensitive requests.",
    capabilities: "Good for quicker responses while keeping a reasoning-first profile.",
  },
  {
    name: "Kimi K2.7 Code",
    slug: "kimi-k2.7-code",
    category: "Coding",
    inputPrice: "$0.00",
    outputPrice: "$0.00",
    description: "Coding-focused model for implementation and editor workflows.",
    capabilities: "Useful for code generation, iteration, and development assistants.",
  },
  {
    name: "GPT-5.4",
    slug: "gpt-5.4",
    category: "General",
    inputPrice: "$0.00",
    outputPrice: "$0.00",
    description: "Stable general model for predictable, standard request patterns.",
    capabilities: "Works well as a dependable fallback in a shared integration surface.",
  },
];
