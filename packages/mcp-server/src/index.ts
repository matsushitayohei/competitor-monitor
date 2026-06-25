import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const server = new McpServer({
  name: 'competitor-monitor',
  version: '1.0.0',
});

// Tool: Get recent changes
server.tool(
  'get_recent_changes',
  'Get competitor UI/UX changes from the last N days',
  { days: z.number().default(7).describe('Number of days to look back') },
  async ({ days }) => {
    const since = new Date();
    since.setDate(since.getDate() - days);

    const { data, error } = await supabase
      .from('changes')
      .select('*')
      .gte('detected_at', since.toISOString())
      .order('detected_at', { ascending: false });

    if (error) return { content: [{ type: 'text', text: Error:  }] };
    return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
  }
);

// Tool: Get change detail
server.tool(
  'get_change_detail',
  'Get detailed information about a specific change including AI advice',
  { change_id: z.string().describe('The ID of the change to retrieve') },
  async ({ change_id }) => {
    const { data, error } = await supabase
      .from('changes')
      .select('*, advice(*)')
      .eq('id', change_id)
      .single();

    if (error) return { content: [{ type: 'text', text: Error:  }] };
    return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
  }
);

// Tool: Get competitor summary
server.tool(
  'get_competitor_summary',
  'Get a summary of changes for a specific competitor service',
  { service_name: z.string().describe('Service name: suumo, athome, or canary') },
  async ({ service_name }) => {
    const { data, error } = await supabase
      .from('changes')
      .select('category, detected_at, summary')
      .eq('service_name', service_name)
      .order('detected_at', { ascending: false })
      .limit(20);

    if (error) return { content: [{ type: 'text', text: Error:  }] };
    return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
  }
);

// Tool: Search changes
server.tool(
  'search_changes',
  'Search changes by category or keyword',
  {
    category: z.enum(['CRO', 'AD_PRODUCT', 'SEO', 'AI', 'OTHER']).optional().describe('Filter by category'),
    keyword: z.string().optional().describe('Search keyword in change summary'),
  },
  async ({ category, keyword }) => {
    let query = supabase.from('changes').select('*').order('detected_at', { ascending: false });

    if (category) query = query.eq('category', category);
    if (keyword) query = query.ilike('summary', %%);

    const { data, error } = await query.limit(20);

    if (error) return { content: [{ type: 'text', text: Error:  }] };
    return { content: [{ type: 'text', text: JSON.stringify(data, null, 2) }] };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Competitor Monitor MCP Server running on stdio');
}

main().catch(console.error);
