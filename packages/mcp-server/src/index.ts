import { config } from "dotenv";
import { resolve } from "path";

// Load apps/web/.env.local first (base config), then override with MCP server's own .env
config({ path: resolve(__dirname, "../../../apps/web/.env.local") });
config({ path: resolve(__dirname, "../.env"), override: true });

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

// --- Press Release Monitor Tools ---

server.tool(
  "query_press_articles",
  "Search press release articles by source name, date range, and relevance category",
  {
    source_name: z.string().optional().describe("Source name to filter by"),
    date_from: z.string().optional().describe("Start date (YYYY-MM-DD format)"),
    date_to: z.string().optional().describe("End date (YYYY-MM-DD format)"),
    category: z
      .enum(["service_feature", "market_data", "ux_improvement", "pricing", "other"])
      .optional()
      .describe("Relevance category"),
    limit: z.number().min(1).max(100).default(20).describe("Maximum results (1-100)"),
  },
  async ({ source_name, date_from, date_to, category, limit }) => {
    // Validate date_from format
    if (date_from !== undefined) {
      const dateFromParsed = Date.parse(date_from);
      if (isNaN(dateFromParsed) || !/^\d{4}-\d{2}-\d{2}$/.test(date_from)) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                error: "parameter 'date_from': invalid date format, expected YYYY-MM-DD",
              }),
            },
          ],
        };
      }
    }

    // Validate date_to format
    if (date_to !== undefined) {
      const dateToParsed = Date.parse(date_to);
      if (isNaN(dateToParsed) || !/^\d{4}-\d{2}-\d{2}$/.test(date_to)) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                error: "parameter 'date_to': invalid date format, expected YYYY-MM-DD",
              }),
            },
          ],
        };
      }
    }

    // Validate source_name if provided
    if (source_name !== undefined) {
      const source = await prisma.pressSource.findFirst({
        where: { name: source_name, deletedAt: null },
      });
      if (!source) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                error: `parameter 'source_name': source '${source_name}' not found`,
              }),
            },
          ],
        };
      }
    }

    // Build where clause
    const where: Record<string, unknown> = { deletedAt: null };

    if (source_name) {
      where.source = { name: source_name, deletedAt: null };
    }

    if (date_from || date_to) {
      const publishedAt: Record<string, Date> = {};
      if (date_from) publishedAt.gte = new Date(date_from);
      if (date_to) {
        const toDate = new Date(date_to);
        toDate.setHours(23, 59, 59, 999);
        publishedAt.lte = toDate;
      }
      where.publishedAt = publishedAt;
    }

    if (category) {
      where.relevanceCategory = category;
    }

    const articles = await prisma.pressArticle.findMany({
      where,
      orderBy: { publishedAt: "desc" },
      take: limit,
      select: {
        title: true,
        articleUrl: true,
        publishedAt: true,
        relevanceCategory: true,
        summary: true,
      },
    });

    // Map articleUrl to url for response format
    const result = articles.map((a) => ({
      title: a.title,
      url: a.articleUrl,
      publishedAt: a.publishedAt,
      relevanceCategory: a.relevanceCategory,
      summary: a.summary,
    }));

    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  "get_latest_press_articles",
  "Get the latest N press release articles for a specific source",
  {
    source_name: z.string().describe("Name of the press source"),
    count: z.number().min(1).max(50).default(10).describe("Number of articles to return (1-50)"),
  },
  async ({ source_name, count }) => {
    // Find source by name
    const source = await prisma.pressSource.findFirst({
      where: { name: source_name, deletedAt: null },
    });

    if (!source) {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              error: `parameter 'source_name': source '${source_name}' not found`,
            }),
          },
        ],
      };
    }

    // Get latest articles ordered by publishedAt DESC
    const articles = await prisma.pressArticle.findMany({
      where: { sourceId: source.id, deletedAt: null },
      orderBy: { publishedAt: "desc" },
      take: count,
      select: {
        title: true,
        articleUrl: true,
        publishedAt: true,
        relevanceCategory: true,
        summary: true,
      },
    });

    // Map articleUrl to url for response format
    const result = articles.map((a) => ({
      title: a.title,
      url: a.articleUrl,
      publishedAt: a.publishedAt,
      relevanceCategory: a.relevanceCategory,
      summary: a.summary,
    }));

    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  "list_press_sources",
  "List all registered press release sources with their active status",
  {},
  async () => {
    const sources = await prisma.pressSource.findMany({
      where: { deletedAt: null },
      orderBy: { createdAt: "asc" },
      select: { id: true, name: true, url: true, isActive: true, createdAt: true },
    });
    return { content: [{ type: "text", text: JSON.stringify(sources, null, 2) }] };
  }
);

// --- Press Insight Tools ---

server.tool(
  "save_press_insight",
  "Save a service improvement insight extracted from a press article. Use this to accumulate actionable ideas for LIFULL HOME'S.",
  {
    article_id: z.string().describe("The PressArticle ID this insight is derived from"),
    insight_type: z
      .enum(["feature_idea", "market_trend", "ux_pattern", "pricing_strategy", "competitive_advantage"])
      .describe("Type of insight"),
    title: z.string().max(200).describe("Short title of the insight (Japanese, max 200 chars)"),
    description: z.string().describe("Detailed description of the insight/initiative"),
    applicability: z.string().optional().describe("How this could apply to LIFULL HOME'S"),
    priority: z.enum(["high", "medium", "low"]).default("medium").describe("Priority level"),
    tags: z.array(z.string()).default([]).describe("Tags for categorization (e.g., ['AI', 'CRO', '賃貸'])"),
    source_competitor: z
      .string()
      .optional()
      .describe("Which competitor this is from (suumo, athome, canary, other)"),
  },
  async ({ article_id, insight_type, title, description, applicability, priority, tags, source_competitor }) => {
    // Verify article exists
    const article = await prisma.pressArticle.findUnique({ where: { id: article_id } });
    if (!article) {
      return {
        content: [{ type: "text", text: JSON.stringify({ error: `Article '${article_id}' not found` }) }],
      };
    }

    const insight = await prisma.pressInsight.create({
      data: {
        articleId: article_id,
        insightType: insight_type,
        title,
        description,
        applicability,
        priority,
        tags,
        sourceCompetitor: source_competitor,
      },
    });

    return {
      content: [{ type: "text", text: JSON.stringify({ created: insight.id, title: insight.title }, null, 2) }],
    };
  }
);

server.tool(
  "get_press_insights",
  "Search and retrieve accumulated service improvement insights from press articles",
  {
    insight_type: z
      .enum(["feature_idea", "market_trend", "ux_pattern", "pricing_strategy", "competitive_advantage"])
      .optional()
      .describe("Filter by insight type"),
    priority: z.enum(["high", "medium", "low"]).optional().describe("Filter by priority"),
    status: z
      .enum(["new", "reviewed", "adopted", "dismissed"])
      .optional()
      .describe("Filter by status"),
    source_competitor: z.string().optional().describe("Filter by competitor (suumo, athome, canary, other)"),
    tag: z.string().optional().describe("Filter by tag (partial match in tags array)"),
    limit: z.number().min(1).max(100).default(20).describe("Max results (1-100)"),
  },
  async ({ insight_type, priority, status, source_competitor, tag, limit }) => {
    const where: Record<string, unknown> = {};

    if (insight_type) where.insightType = insight_type;
    if (priority) where.priority = priority;
    if (status) where.status = status;
    if (source_competitor) where.sourceCompetitor = source_competitor;
    if (tag) {
      // Prisma JSON filter for PostgreSQL: check if tags array contains the value
      where.tags = { array_contains: [tag] };
    }

    const insights = await prisma.pressInsight.findMany({
      where,
      orderBy: { createdAt: "desc" },
      take: limit,
      include: {
        article: {
          select: { title: true, articleUrl: true, publishedAt: true, source: { select: { name: true } } },
        },
      },
    });

    const result = insights.map((i) => ({
      id: i.id,
      insightType: i.insightType,
      title: i.title,
      description: i.description,
      applicability: i.applicability,
      priority: i.priority,
      status: i.status,
      tags: i.tags,
      sourceCompetitor: i.sourceCompetitor,
      createdAt: i.createdAt,
      article: {
        title: i.article.title,
        url: i.article.articleUrl,
        publishedAt: i.article.publishedAt,
        sourceName: i.article.source.name,
      },
    }));

    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  "update_press_insight_status",
  "Update the status of a press insight (e.g., mark as reviewed, adopted, or dismissed)",
  {
    insight_id: z.string().describe("The PressInsight ID to update"),
    status: z.enum(["new", "reviewed", "adopted", "dismissed"]).describe("New status"),
  },
  async ({ insight_id, status }) => {
    const existing = await prisma.pressInsight.findUnique({ where: { id: insight_id } });
    if (!existing) {
      return { content: [{ type: "text", text: JSON.stringify({ error: `Insight '${insight_id}' not found` }) }] };
    }

    const updated = await prisma.pressInsight.update({
      where: { id: insight_id },
      data: { status },
    });

    return {
      content: [{ type: "text", text: JSON.stringify({ updated: updated.id, status: updated.status }, null, 2) }],
    };
  }
);

// --- UIUX Structure Tools ---

server.tool(
  "get_page_structure",
  "Get the latest UIUX component structure of a competitor page",
  {
    service: z.string().describe("Service name: suumo, athome, or canary"),
    page_type: z.string().describe("Page type: detail, list, form, top"),
    device: z.string().default("sp").describe("Device: pc or sp"),
    depth: z.enum(["summary", "full"]).default("summary").describe("Level of detail: summary or full (all components)"),
  },
  async ({ service, page_type, device, depth }) => {
    const page = await prisma.monitoredPage.findFirst({
      where: {
        service: { name: service },
        pageType: page_type,
        device: device,
        isActive: true,
        deletedAt: null,
      },
      select: { id: true, url: true },
    });

    if (!page) {
      return { content: [{ type: "text", text: JSON.stringify({ error: `No active page found for ${service}/${page_type}/${device}` }) }] };
    }

    const structure = await prisma.pageStructure.findFirst({
      where: { pageId: page.id },
      orderBy: { capturedAt: "desc" },
    });

    if (!structure) {
      return { content: [{ type: "text", text: JSON.stringify({ error: "No structure data available yet." }) }] };
    }

    const result: Record<string, unknown> = {
      service,
      pageType: page_type,
      device,
      url: page.url,
      capturedAt: structure.capturedAt,
      summary: structure.structureSummary,
      componentCount: structure.componentCount,
      cvPoints: structure.cvPoints,
    };

    if (depth === "full") {
      result.sections = structure.sections;
      result.formAnalysis = structure.formAnalysis;
    }

    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  "get_own_page_structure",
  "Get the latest UIUX component structure of a LIFULL HOME'S page",
  {
    page_type: z.string().describe("Page type: detail, list, form, top"),
    device: z.string().default("sp").describe("Device: pc or sp"),
    category: z.string().default("chintai").describe("Category: chintai, buy, etc."),
    depth: z.enum(["summary", "full"]).default("summary").describe("Level of detail"),
  },
  async ({ page_type, device, category, depth }) => {
    const ownPage = await prisma.ownPage.findFirst({
      where: { pageType: page_type, device, category, isActive: true, deletedAt: null },
      select: { id: true, name: true, url: true },
    });

    if (!ownPage) {
      return { content: [{ type: "text", text: JSON.stringify({ error: `No HOME'S page found for ${page_type}/${device}/${category}` }) }] };
    }

    const structure = await prisma.ownPageStructure.findFirst({
      where: { ownPageId: ownPage.id },
      orderBy: { capturedAt: "desc" },
    });

    if (!structure) {
      return { content: [{ type: "text", text: JSON.stringify({ error: "No structure data available yet." }) }] };
    }

    const result: Record<string, unknown> = {
      service: "homes",
      pageName: ownPage.name,
      pageType: page_type,
      device,
      category,
      url: ownPage.url,
      capturedAt: structure.capturedAt,
      summary: structure.structureSummary,
      componentCount: structure.componentCount,
      cvPoints: structure.cvPoints,
    };

    if (depth === "full") {
      result.sections = structure.sections;
      result.formAnalysis = structure.formAnalysis;
    }

    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  "compare_with_homes",
  "Compare a competitor page structure with HOME'S to identify gaps and opportunities",
  {
    service: z.string().describe("Competitor: suumo, athome, or canary"),
    page_type: z.string().describe("Page type: detail, list, form"),
    device: z.string().default("sp").describe("Device: pc or sp"),
  },
  async ({ service, page_type, device }) => {
    const competitorPage = await prisma.monitoredPage.findFirst({
      where: { service: { name: service }, pageType: page_type, device, isActive: true, deletedAt: null },
      select: { id: true, url: true },
    });

    const competitorStructure = competitorPage
      ? await prisma.pageStructure.findFirst({ where: { pageId: competitorPage.id }, orderBy: { capturedAt: "desc" } })
      : null;

    const ownPage = await prisma.ownPage.findFirst({
      where: { pageType: page_type, device, isActive: true, deletedAt: null },
      select: { id: true, url: true, name: true },
    });

    const ownStructure = ownPage
      ? await prisma.ownPageStructure.findFirst({ where: { ownPageId: ownPage.id }, orderBy: { capturedAt: "desc" } })
      : null;

    if (!competitorStructure && !ownStructure) {
      return { content: [{ type: "text", text: JSON.stringify({ error: "No structure data available." }) }] };
    }

    const comparison = {
      competitor: {
        service,
        pageType: page_type,
        device,
        url: competitorPage?.url,
        summary: competitorStructure?.structureSummary ?? null,
        cvPoints: competitorStructure?.cvPoints ?? null,
        formAnalysis: competitorStructure?.formAnalysis ?? null,
        componentCount: competitorStructure?.componentCount ?? 0,
      },
      homes: {
        pageName: ownPage?.name,
        url: ownPage?.url,
        summary: ownStructure?.structureSummary ?? null,
        cvPoints: ownStructure?.cvPoints ?? null,
        formAnalysis: ownStructure?.formAnalysis ?? null,
        componentCount: ownStructure?.componentCount ?? 0,
      },
    };

    return { content: [{ type: "text", text: JSON.stringify(comparison, null, 2) }] };
  }
);

server.tool(
  "get_form_comparison",
  "Compare form structures across competitors and HOME'S",
  {
    service: z.string().optional().describe("Specific competitor (omit for all)"),
    device: z.string().default("sp").describe("Device: pc or sp"),
  },
  async ({ service, device }) => {
    const services = service ? [service] : ["suumo", "athome", "canary"];
    const results: Record<string, unknown>[] = [];

    for (const svc of services) {
      const page = await prisma.monitoredPage.findFirst({
        where: { service: { name: svc }, pageType: "form", device, isActive: true, deletedAt: null },
        select: { id: true, url: true },
      });

      if (page) {
        const structure = await prisma.pageStructure.findFirst({
          where: { pageId: page.id },
          orderBy: { capturedAt: "desc" },
          select: { formAnalysis: true, cvPoints: true, capturedAt: true },
        });
        results.push({ service: svc, url: page.url, formAnalysis: structure?.formAnalysis, cvPoints: structure?.cvPoints, capturedAt: structure?.capturedAt });
      }
    }

    const ownPage = await prisma.ownPage.findFirst({
      where: { pageType: "form", device, isActive: true, deletedAt: null },
      select: { id: true, url: true, name: true },
    });

    if (ownPage) {
      const ownStructure = await prisma.ownPageStructure.findFirst({
        where: { ownPageId: ownPage.id },
        orderBy: { capturedAt: "desc" },
        select: { formAnalysis: true, cvPoints: true, capturedAt: true },
      });
      results.push({ service: "homes", pageName: ownPage.name, url: ownPage.url, formAnalysis: ownStructure?.formAnalysis, cvPoints: ownStructure?.cvPoints, capturedAt: ownStructure?.capturedAt });
    }

    return { content: [{ type: "text", text: JSON.stringify(results, null, 2) }] };
  }
);

server.tool(
  "get_cv_gaps",
  "Get CV elements that competitors have but HOME'S doesn't",
  {
    page_type: z.string().optional().describe("Filter by page type (detail, list, form)"),
    device: z.string().default("sp").describe("Device: pc or sp"),
  },
  async ({ page_type, device }) => {
    const pageTypes = page_type ? [page_type] : ["detail", "list", "form"];
    const gaps: Record<string, unknown>[] = [];

    for (const pt of pageTypes) {
      const competitorPages = await prisma.monitoredPage.findMany({
        where: { pageType: pt, device, isActive: true, deletedAt: null },
        select: { id: true, service: { select: { name: true } } },
      });

      const competitorCvTypes = new Set<string>();
      for (const cp of competitorPages) {
        const structure = await prisma.pageStructure.findFirst({
          where: { pageId: cp.id },
          orderBy: { capturedAt: "desc" },
          select: { cvPoints: true },
        });
        if (structure?.cvPoints) {
          const cv = structure.cvPoints as { cvPoints?: Array<{ type: string }> };
          if (cv.cvPoints) {
            for (const point of cv.cvPoints) {
              competitorCvTypes.add(point.type);
            }
          }
        }
      }

      const ownPage = await prisma.ownPage.findFirst({
        where: { pageType: pt, device, isActive: true, deletedAt: null },
        select: { id: true },
      });

      const ownCvTypes = new Set<string>();
      if (ownPage) {
        const ownStructure = await prisma.ownPageStructure.findFirst({
          where: { ownPageId: ownPage.id },
          orderBy: { capturedAt: "desc" },
          select: { cvPoints: true },
        });
        if (ownStructure?.cvPoints) {
          const cv = ownStructure.cvPoints as { cvPoints?: Array<{ type: string }> };
          if (cv.cvPoints) {
            for (const point of cv.cvPoints) {
              ownCvTypes.add(point.type);
            }
          }
        }
      }

      const missing = [...competitorCvTypes].filter(t => !ownCvTypes.has(t));
      if (missing.length > 0) {
        gaps.push({ pageType: pt, device, missingCvElements: missing, competitorHas: [...competitorCvTypes], homesHas: [...ownCvTypes] });
      }
    }

    return { content: [{ type: "text", text: JSON.stringify(gaps, null, 2) }] };
  }
);

server.tool(
  "get_structure_history",
  "Get structure change history for a page over time",
  {
    service: z.string().describe("Service: suumo, athome, canary, or homes"),
    page_type: z.string().describe("Page type: detail, list, form"),
    device: z.string().default("sp").describe("Device: pc or sp"),
    limit: z.number().default(10).describe("Max records to return"),
  },
  async ({ service, page_type, device, limit }) => {
    if (service === "homes") {
      const ownPage = await prisma.ownPage.findFirst({
        where: { pageType: page_type, device, isActive: true, deletedAt: null },
        select: { id: true, name: true, url: true },
      });

      if (!ownPage) {
        return { content: [{ type: "text", text: JSON.stringify({ error: "Page not found" }) }] };
      }

      const history = await prisma.ownPageStructure.findMany({
        where: { ownPageId: ownPage.id },
        orderBy: { capturedAt: "desc" },
        take: limit,
        select: { capturedAt: true, structureSummary: true, componentCount: true, hash: true },
      });

      return { content: [{ type: "text", text: JSON.stringify({ service, pageName: ownPage.name, url: ownPage.url, history }, null, 2) }] };
    }

    const page = await prisma.monitoredPage.findFirst({
      where: { service: { name: service }, pageType: page_type, device, isActive: true, deletedAt: null },
      select: { id: true, url: true },
    });

    if (!page) {
      return { content: [{ type: "text", text: JSON.stringify({ error: "Page not found" }) }] };
    }

    const history = await prisma.pageStructure.findMany({
      where: { pageId: page.id },
      orderBy: { capturedAt: "desc" },
      take: limit,
      select: { capturedAt: true, structureSummary: true, componentCount: true, hash: true },
    });

    return { content: [{ type: "text", text: JSON.stringify({ service, url: page.url, history }, null, 2) }] };
  }
);

server.tool(
  "delete_noise_changes",
  "Delete noise/false-positive change records (e.g., CSRF token or build hash fluctuations). Deletes changes and their associated advice records.",
  {
    priority: z.enum(["low", "medium", "high"]).optional().describe("Filter by advice priority level to delete"),
    summary_contains: z.string().optional().describe("Filter by summary containing this text"),
    before_date: z.string().optional().describe("Delete changes detected before this ISO date"),
    dry_run: z.boolean().default(true).describe("If true, only count records without deleting"),
  },
  async ({ priority, summary_contains, before_date, dry_run }) => {
    const where: any = {};
    if (before_date) {
      where.detectedAt = { lt: new Date(before_date) };
    }
    if (priority || summary_contains) {
      where.advice = {};
      if (priority) where.advice.priority = priority;
      if (summary_contains) where.advice.summary = { contains: summary_contains };
    }

    const count = await prisma.change.count({ where });

    if (dry_run) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ dry_run: true, matching_records: count, message: `${count} records would be deleted. Set dry_run=false to execute.` }, null, 2),
        }],
      };
    }

    // Delete advice first (FK constraint), then changes
    const changeIds = await prisma.change.findMany({ where, select: { id: true } });
    const ids = changeIds.map((c) => c.id);

    const deletedAdvice = await prisma.advice.deleteMany({ where: { changeId: { in: ids } } });
    const deletedChanges = await prisma.change.deleteMany({ where: { id: { in: ids } } });

    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          dry_run: false,
          deleted_changes: deletedChanges.count,
          deleted_advice: deletedAdvice.count,
        }, null, 2),
      }],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Competitor Monitor MCP Server running on stdio");
}

main().catch(console.error);
