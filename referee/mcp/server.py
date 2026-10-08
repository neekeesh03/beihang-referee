from __future__ import annotations

def build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError('MCP support requires the optional `mcp` package') from exc
    from ..ingestion import PackageInspector
    from ..comparison import revision_diff, audit_rebuttal_structure
    from ..documents import DocumentLoader
    from ..modes import ReviewModeRegistry

    mcp=FastMCP('Referee')

    @mcp.tool()
    def inspect_package(paths:list[str])->dict:
        """Inspect manuscript/reproducibility package structure without running a model."""
        return PackageInspector().inspect(paths).to_dict()

    @mcp.tool()
    def compare_revision(old_path:str,new_path:str)->dict:
        """Compare two manuscript versions structurally."""
        loader=DocumentLoader();return revision_diff(loader.load(old_path).text,loader.load(new_path).text)

    @mcp.tool()
    def audit_rebuttal(response_path:str)->dict:
        """Audit reviewer-response traceability signals."""
        return audit_rebuttal_structure(DocumentLoader().load(response_path).text)

    @mcp.tool()
    def list_review_modes()->list[str]:
        return ReviewModeRegistry().names()
    return mcp

def main():
    build_server().run()

if __name__=='__main__':main()
