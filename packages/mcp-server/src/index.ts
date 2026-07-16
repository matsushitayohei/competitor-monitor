import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

const server = new McpServer({
  name: "competitor-monitor",
  version: "1.0.0",
});

server.tool(
  "get_recent_changes",
  "Get competitor UI/UX changes from the last N days",
  { days: z.number().default(7).describe("Number of days to look back") },
  async ({ days }) => {
    const since = new Date();
    since.setDate(since.getDate() - days);
    const changes = await prisma.change.findMany({
      where: { detectedAt: { gte: since } },
      orderBy: { detectedAt: "desc" },
      include: { advice: true },
    });
    return { content: [{ type: "text", text: JSON.stringify(changes, null, 2) }] };
  }
);

server.tool(
  "get_change_detail",
  "Get detailed information about a specific change including AI advice",
  { change_id: z.string().describe("The ID of the change to retrieve") },
  async ({ change_id }) => {
    const change = await prisma.change.findUnique({
      where: { id: change_id },
      include: { advice: true, page: { include: { service: true } } },
    });
    if (!change) return { content: [{ type: "text", text: "Change not found" }] };
    return { content: [{ type: "text", text: JSON.stringify(change, null, 2) }] };
  }
);

server.tool(
  "get_competitor_summary",
  "Get a summary of changes for a specific competitor service",
  { service_name: z.string().describe("Service name: suumo, athome, or canary") },
  async ({ service_name }) => {
    const changes = await prisma.change.findMany({
      where: { serviceName: service_name },
      orderBy: { detectedAt: "desc" },
      take: 20,
      select: { category: true, detectedAt: true, summary: true },
    });
    return { content: [{ type: "text", text: JSON.stringify(changes, null, 2) }] };
  }
);

server.tool(
  "search_changes",
  "Search changes by category or keyword",
  {
    category: z.enum(["CRO", "AD_PRODUCT", "SEO", "AI", "OTHER"]).optional(),
    keyword: z.string().optional().describe("Search keyword in change summary"),
  },
  async ({ category, keyword }) => {
    const changes = await prisma.change.findMany({
      where: {
        ...(category && { category }),
        ...(keyword && { summary: { contains: keyword, mode: "insensitive" } }),
      },
      orderBy: { detectedAt: "desc" },
      take: 20,
    });
    return { content: [{ type: "text", text: JSON.stringify(changes, null, 2) }] };
  }
);

server.tool(
  "get_unanalyzed_changes",
  "Get changes that have not been analyzed by Kiro yet (advice.proposal contains 'MCP経由')",
  { limit: z.number().default(10).describe("Max number of changes to return") },
  async ({ limit }) => {
    const changes = await prisma.change.findMany({
      where: {
        advice: {
          proposal: { contains: "MCP経由" },
        },
      },
      orderBy: { detectedAt: "desc" },
      take: limit,
      include: {
        advice: true,
        page: { include: { service: true } },
      },
    });
    return { content: [{ type: "text", text: JSON.stringify(changes, null, 2) }] };
  }
);

server.tool(
  "get_change_diff",
  "Get the full DOM diff text for a change (for Kiro to analyze)",
  { change_id: z.string().describe("The ID of the change") },
  async ({ change_id }) => {
    const change = await prisma.change.findUnique({
      where: { id: change_id },
      select: {
        id: true,
        serviceName: true,
        pageType: true,
        category: true,
        summary: true,
        diffText: true,
        detectedAt: true,
        page: { select: { url: true, device: true } },
      },
    });
    if (!change) return { content: [{ type: "text", text: "Change not found" }] };
    return { content: [{ type: "text", text: JSON.stringify(change, null, 2) }] };
  }
);

server.tool(
  "save_kiro_advice",
  "Save Kiro-generated advice for a change (updates existing advice record)",
  {
    change_id: z.string().describe("The ID of the change"),
    summary: z.string().describe("What changed (1-2 sentences in Japanese)"),
    intent: z.string().describe("Why the competitor likely made this change"),
    proposal: z.string().describe("How LIFULL HOME'S could adopt this"),
    priority: z.enum(["high", "medium", "low"]).describe("Priority level"),
    expected_effect: z.string().optional().describe("Expected impact if adopted"),
    risks: z.string().optional().describe("Potential risks or concerns"),
  },
  async ({ change_id, summary, intent, proposal, priority, expected_effect, risks }) => {
    const existing = await prisma.advice.findUnique({
      where: { changeId: change_id },
    });

    if (existing) {
      const updated = await prisma.advice.update({
        where: { changeId: change_id },
        data: { summary, intent, proposal, priority, expectedEffect: expected_effect, risks },
      });
      return { content: [{ type: "text", text: `Advice updated: ${updated.id}` }] };
    } else {
      const created = await prisma.advice.create({
        data: {
          changeId: change_id,
          summary,
          intent,
          proposal,
          priority,
          expectedEffect: expected_effect,
          risks,
        },
      });
      return { content: [{ type: "text", text: `Advice created: ${created.id}` }] };
    }
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Competitor Monitor MCP Server running on stdio");
}

main().catch(console.error);
