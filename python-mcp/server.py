from mcp.server.fastmcp import FastMCP
import logging
from config import settings

# Import all tools
import tools.media as media_tools
import tools.documents as doc_tools
import tools.location as loc_tools
import tools.dates as date_tools
import tools.pinecone_tools as pinecone_tools
import tools.model_router as router_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

# Initialize FastMCP Server
mcp = FastMCP("Pomoshnik-Tools")

logger.info("Registering tools...")

# Register Media Tools
mcp.tool()(media_tools.analyze_image)
mcp.tool()(media_tools.analyze_video)
mcp.tool()(media_tools.analyze_audio)
mcp.tool()(media_tools.decode_qr_barcode)

# Register Document Tools
mcp.tool()(doc_tools.analyze_document)
mcp.tool()(doc_tools.process_link)

# Register Location Tools
mcp.tool()(loc_tools.reverse_geocode)

# Register Date Tools
mcp.tool()(date_tools.extract_dates_and_events)

# Register Pinecone Tools
mcp.tool()(pinecone_tools.search_memory)
mcp.tool()(pinecone_tools.save_to_memory)
mcp.tool()(pinecone_tools.get_memory_stats)

# Register Model Routing
mcp.tool()(router_tools.smart_analyze)

if __name__ == "__main__":
    logger.info("Starting FastMCP server via stdio transport...")
    # OpenClaw expects stdio transport for MCP
    mcp.run(transport='stdio')
