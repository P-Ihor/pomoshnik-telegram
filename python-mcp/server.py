from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import logging
from config import settings

# Import all tools
import tools.media as media_tools
import tools.documents as doc_tools
import tools.location as loc_tools
import tools.dates as date_tools
import tools.pinecone_tools as pinecone_tools
import tools.model_router as router_tools
import tools.google_calendar as calendar_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

import tools.web_search as web_search_tools

# Initialize FastMCP Server with disabled DNS rebinding protection for Docker networking
mcp = FastMCP(
    "Pomoshnik-Tools",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)
)
mcp.settings.stateless_http = True

logger.info("Registering tools...")

# Register Web Search Tool
mcp.tool()(web_search_tools.perform_web_search)

# Register Media Tools
# mcp.tool()(media_tools.analyze_image) # Removed: LLMs truncate huge base64 strings. Agent has native vision.
mcp.tool()(media_tools.analyze_video)
mcp.tool()(media_tools.analyze_audio)
# mcp.tool()(media_tools.decode_qr_barcode) # Removed for the same reason.

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

# Register Calendar Tools
calendar_tools.register(mcp)

# Register Telegram Tools
import tools.telegram as telegram_tools
mcp.tool()(telegram_tools.send_telegram_media)

if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    logger.info("Starting FastMCP server via streamable-http transport...")
    # Get the ASGI app from FastMCP and serve it with uvicorn
    # Allow all hosts since we're behind Docker internal network
    app = mcp.streamable_http_app()
    # Wrap with middleware that allows any host (needed for Docker container-to-container)
    uvicorn.run(app, host="0.0.0.0", port=8000, forwarded_allow_ips="*")
