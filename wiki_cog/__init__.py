import json
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import pagify
import discord
import aiohttp
import asyncio
from typing import Optional, List, Dict, Any
import re
from bs4 import BeautifulSoup
import html

class WikiCog(commands.Cog):
    """Wiki search cog for open.mp documentation"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        
        # Algolia search configuration
        self.algolia_app_id = "AOKXGK39Z7"
        self.algolia_api_key = "54204f37e5c8fc2871052d595ee0505e"
        self.algolia_index_name = "open"
        

    def truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length"""
        if len(text) <= max_length:
            return text
        return text[:text.rfind(' ', max_length)] + ' ...'

    def format_description(self, content: str) -> str:
        """Format description by replacing mark tags"""
        return content.replace('<mark>', '**').replace('</mark>', '**')

    def decode_html_entities(self, text: str) -> str:
        """Decode HTML entities"""
        return html.unescape(text)

    async def parse_openmp_doc_content(self, url: str) -> str:
        """Parse OpenMP documentation content from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return "Error fetching content. Please check the documentation website directly."
                    
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    final_content = ''
                    
                    title_elem = soup.find('h1')
                    if title_elem:
                        final_content += f"# {title_elem.get_text().strip()}\n\n"
                    
                    
                    article = soup.find('article')
                    if not article:
                        return "Could not find article content."
                    
                    desc_elem = article.find('p')
                    if desc_elem:
                        description = desc_elem.get_text().strip()
                        if description:
                            final_content += f"## Description\n{description}\n\n"
                    
                    params_table = article.find('table')
                    if params_table:
                        final_content += "## Parameters\n"
                        
                        rows = params_table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                param_name = cells[0].get_text().strip()
                                param_desc = cells[1].get_text().strip()
                                
                                if (param_name and param_name != 'Name' and 
                                    param_desc and param_desc != 'Description'):
                                    final_content += f"- **{param_name}**: {param_desc}\n"
                        
                        final_content += '\n'
                    
                    code_blocks = article.find_all(['pre', 'code'])
                    if code_blocks:
                        final_content += "## Examples\n"
                        
                        for block in code_blocks:
                            if block.name == 'pre':
                                code_elem = block.find('code')
                                if code_elem:
                                    code = code_elem.get_text()
                                else:
                                    code = block.get_text()
                            else:
                                code = block.get_text()
                            
                            code = self.decode_html_entities(code.strip())
                            
                            if re.match(r'^\s*\d+\s+', code, re.MULTILINE):
                                lines = code.split('\n')
                                cleaned_lines = [re.sub(r'^\s*\d+\s+', '', line) for line in lines]
                                code = '\n'.join(cleaned_lines)
                            
                            language = 'pawn'
                            if block.get('class'):
                                if 'language-c' in block.get('class', []):
                                    language = 'c'
                                elif 'language-cpp' in block.get('class', []):
                                    language = 'cpp'
                            
                            final_content += f"```{language}\n{code}\n```\n\n"
                    
                    notes_pattern = re.search(
                        r'Notes[,\s]*([\s\S]*?)(?=Related Functions|Related Callbacks|Tags|$)',
                        article.get_text(),
                        re.IGNORECASE
                    )
                    if notes_pattern and notes_pattern.group(1):
                        notes_text = notes_pattern.group(1).strip()
                        
                        tip_match = re.search(r'Tip:?\s*([\s\S]*?)(?=Warning:|Related Callbacks|$)', notes_text, re.IGNORECASE)
                        warning_match = re.search(r'Warning:?\s*([\s\S]*?)(?=Related Callbacks|$)', notes_text, re.IGNORECASE)
                        
                        final_content += "## Notes\n"
                        
                        if tip_match and tip_match.group(1).strip():
                            tip_text = tip_match.group(1).strip()
                            final_content += f"**:bulb: Tip:** {tip_text}\n\n"
                        
                        if warning_match and warning_match.group(1).strip():
                            warning_text = warning_match.group(1).strip()
                            warning_text = re.sub(r'^warning\s*you', 'You', warning_text, flags=re.IGNORECASE)
                            final_content += f"**:warning: Warning:** {warning_text}\n\n"
                    
                    final_content = re.sub(r'\n{3,}', '\n\n', final_content)
                    final_content = re.sub(r'\s+\n', '\n', final_content)
                    final_content = re.sub(r'Edit this page.*$', '', final_content, flags=re.MULTILINE)
                    final_content = final_content.strip()
                    
                    return final_content
                    
        except Exception as e:
            return f"Error fetching content: {str(e)}"

    async def search_documentation(self, query: str, language: str = "en") -> List[Dict[str, Any]]:
        """Search the documentation using Algolia"""
        try:
            search_data = {
                "params": f"hitsPerPage=20&filters=language:{language}",
                "query": query
            }
            
            headers = {
                'X-Algolia-API-Key': self.algolia_api_key,
                'X-Algolia-Application-Id': self.algolia_app_id,
                'Content-Type': 'application/json'
            }
            
            url = f"https://{self.algolia_app_id}-dsn.algolia.net/1/indexes/{self.algolia_index_name}/query"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=search_data, headers=headers) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    return data.get('hits', [])
                    
        except Exception as e:
            print(f"Error searching documentation: {e}")
            return []

    @commands.command(name="wiki")
    async def wiki_search(self, ctx: commands.Context, *, search_term: str):
        """Search the open.mp wiki documentation"""
        if len(search_term) < 3:
            await ctx.send("Query must be 3 characters or more")
            return
        
        language = "en"
        results = await self.search_documentation(search_term, language)
        
        if not results:
            embed = discord.Embed(
                title=f"No results: {search_term}",
                description="There were no results for that query.",
                color=0x0099ff
            )
            await ctx.send(embed=embed)
            return
        
        filtered_results = []
        seen_urls = set()
        
        for hit in results:
            url = hit.get('url_without_anchor', '')
            if url in seen_urls:
                continue
            
            seen_urls.add(url)
            
            url_parts = url.rstrip('/').split('/')
            if len(url_parts) < 2:
                continue
            
            if (url_parts[-2] == 'blog' or 
                'tags' in url_parts or
                url_parts[-1].startswith('omp-') or
                url_parts[-1] in ['functions', 'callbacks', 'natives', 'constants', 'libraries']):
                continue
            
            allowed_types = ['functions', 'callbacks', 'natives', 'constants', 'libraries']
            if not any(t in url_parts for t in allowed_types):
                continue
            
            filtered_results.append(hit)
            if len(filtered_results) >= 10:
                break
        
        if not filtered_results:
            embed = discord.Embed(
                title=f"No results: {search_term}",
                description="There were no results for that query.",
                color=0x0099ff
            )
            await ctx.send(embed=embed)
            return
        
        description = ""
        for i, hit in enumerate(filtered_results[:5], 1):
            url_parts = hit['url_without_anchor'].rstrip('/').split('/')
            name = url_parts[-1]
            
            type_name = ""
            if 'functions' in url_parts:
                type_name = "Function"
            elif 'callbacks' in url_parts:
                type_name = "Callback"
            elif 'natives' in url_parts:
                type_name = "Native"
            elif 'constants' in url_parts:
                type_name = "Constant"
            elif 'libraries' in url_parts:
                type_name = "Library"
            
            desc = "(No description found)"
            if hit.get('content'):
                desc = self.format_description(hit['content'])
            elif hit.get('hierarchy', {}).get('lvl1'):
                desc = hit['hierarchy']['lvl1']
            elif hit.get('description'):
                desc = hit['description']
            elif hit.get('text'):
                desc = hit['text']
            elif hit.get('snippet'):
                desc = hit['snippet']
            
            desc = re.sub(r'<[^>]*>', '', desc)
            if desc in ['undefined', 'null']:
                desc = "(No description found)"
            
            description += f"**{i}.** [**{name}**]({hit['url_without_anchor']})"
            if type_name:
                description += f" `{type_name}`"
            description += "\n"
            description += f"{self.truncate_text(desc, 120)}\n\n"
        
        title = f'Documentation Search Results: "{search_term}"'
        footer_text = 'Click a number to view the full documentation'
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x0099ff
        )
        embed.set_footer(text=footer_text)
        
        
        menu_pages = []
        for i, hit in enumerate(filtered_results[:5]):
            page_content = await self.parse_openmp_doc_content(hit['url_without_anchor'])
            url_parts = hit['url_without_anchor'].rstrip('/').split('/')
            title = url_parts[-1]
            
            pages = list(pagify(page_content, delims=["\n\n", "\n"], page_length=4000))
            for j, page in enumerate(pages):
                embed_page = discord.Embed(
                    title=title if j == 0 else f"{title} (Page {j+1})",
                    description=page,
                    color=0x0099ff,
                    url=hit['url_without_anchor']
                )
                if j == len(pages) - 1:
                    embed_page.set_footer(text="Documentation from open.mp")
                menu_pages.append(embed_page)
        
        if menu_pages:
            await menus.menu(ctx, menu_pages, menus.DEFAULT_CONTROLS, timeout=60.0)
        else:
            await ctx.send(embed=embed)


    @commands.command(name="wikisetup")
    @commands.is_owner()
    async def wiki_setup(self, ctx: commands.Context):
        """Setup the wiki cog configuration"""
        await ctx.send("Wiki cog setup complete! Use `[p]wiki <search term>` to search the documentation.")
