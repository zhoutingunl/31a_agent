#!/usr/bin/env python3
"""
网易云音乐 MCP 控制器 - 简化版（不依赖 FastMCP）
支持 URL scheme 启动和全局快捷键控制
"""

import json
import sys
import os
import logging
from typing import Dict, Any

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir) if os.path.basename(current_dir) == 'src' else current_dir
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from utils.config_manager import (
        load_hotkeys_config,
        load_custom_playlists,
        load_playlists_from_file,
        save_playlists_to_file,
        load_netease_config,
        save_netease_config,
        get_platform
    )
    from utils.music_search import (
        search_netease_music,
        search_netease_playlist,
        generate_play_url,
        generate_playlist_play_url
    )
    from controllers.netease_controller import NeteaseMusicController
    from controllers.daily_controller import DailyRecommendController, SELENIUM_AVAILABLE
except ImportError as e:
    print(f"导入模块失败: {e}", file=sys.stderr)
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量
USER_CUSTOM_PLAYLISTS = {}
_daily_controller = None

# 初始化控制器
def _initialize_controller():
    """初始化音乐控制器"""
    hotkeys = load_hotkeys_config()
    return NeteaseMusicController(hotkeys)

# 创建控制器实例
music_controller = _initialize_controller()

def set_custom_playlists(playlists_dict):
    """设置用户自定义歌单"""
    global USER_CUSTOM_PLAYLISTS
    USER_CUSTOM_PLAYLISTS = playlists_dict or {}
    logger.info(f"已设置 {len(USER_CUSTOM_PLAYLISTS)} 个自定义歌单")

# ============ MCP 工具定义 ============

def launch_netease_music(minimize_window: bool = True) -> dict:
    """启动网易云音乐应用"""
    try:
        scheme_url = music_controller.url_schemes["open"]
        success = music_controller.launch_by_url_scheme(scheme_url, minimize_window)
        
        if success:
            return {
                "success": True,
                "data": {
                    "scheme_url": scheme_url,
                    "minimized": minimize_window,
                    "platform": get_platform()
                },
                "message": "网易云音乐启动成功"
            }
        else:
            return {
                "success": False,
                "error": "网易云音乐启动失败"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"启动网易云音乐时出错: {str(e)}"
        }

def control_playback(action: str = "play_pause") -> dict:
    """控制网易云音乐播放"""
    try:
        valid_actions = ["play_pause", "previous", "next"]
        if action not in valid_actions:
            return {
                "success": False,
                "error": f"无效的action参数: {action}，支持的值: {', '.join(valid_actions)}"
            }
        
        success = music_controller.send_global_hotkey(action)
        
        if success:
            return {
                "success": True,
                "data": {
                    "action": action,
                    "hotkey": music_controller.get_hotkey_for_action(action),
                    "platform": get_platform()
                },
                "message": f"播放控制成功 - {action}"
            }
        else:
            return {
                "success": False,
                "error": f"播放控制失败 - {action}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"播放控制时出错: {str(e)}"
        }

def search_and_play(query: str, minimize_window: bool = True) -> dict:
    """搜索歌曲并直接播放"""
    try:
        song_id, song_name, artist_name = search_netease_music(query)
        
        if not song_id:
            return {
                "success": False,
                "error": f"未找到歌曲: {query}"
            }
        
        play_url = generate_play_url(song_id)
        
        if not play_url:
            return {
                "success": False,
                "error": "生成播放URL失败"
            }
        
        success = music_controller.launch_by_url_scheme(play_url, minimize_window)
        
        if success:
            return {
                "success": True,
                "data": {
                    "query": query,
                    "song_name": song_name,
                    "artist": artist_name,
                    "song_id": song_id,
                    "play_url": play_url,
                    "minimized": minimize_window,
                    "platform": get_platform()
                },
                "message": f"成功播放: 《{song_name}》- {artist_name}"
            }
        else:
            return {
                "success": False,
                "error": f"播放失败: 《{song_name}》- {artist_name}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"搜索播放歌曲时出错: {str(e)}"
        }

def get_controller_info() -> dict:
    """获取控制器信息"""
    try:
        custom_playlists = load_custom_playlists()
        
        return {
            "success": True,
            "data": {
                "server_name": "网易云音乐控制器",
                "platform": get_platform(),
                "hotkey_available": music_controller.is_hotkey_available(),
                "window_control_available": music_controller.is_window_control_available(),
                "selenium_available": SELENIUM_AVAILABLE,
                "supported_actions": music_controller.get_supported_actions(),
                "hotkey_mappings": music_controller.hotkeys,
                "url_schemes": list(music_controller.url_schemes.keys()),
                "custom_playlists": custom_playlists,
                "custom_playlists_count": len(custom_playlists)
            },
            "message": "控制器信息获取成功"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"获取控制器信息时出错: {str(e)}"
        }

# ============ 简单的 MCP 协议实现 ============

def handle_mcp_request(request: dict) -> dict:
    """处理 MCP 请求"""
    method = request.get("method", "")
    params = request.get("params", {})
    
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "launch_netease_music",
                        "description": "启动网易云音乐应用",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "minimize_window": {
                                    "type": "boolean",
                                    "description": "是否自动最小化窗口",
                                    "default": True
                                }
                            }
                        }
                    },
                    {
                        "name": "control_playback",
                        "description": "控制网易云音乐播放",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "description": "播放控制动作",
                                    "enum": ["play_pause", "previous", "next"],
                                    "default": "play_pause"
                                }
                            }
                        }
                    },
                    {
                        "name": "search_and_play",
                        "description": "搜索歌曲并直接播放",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "搜索关键词（歌曲名或歌曲名+歌手）"
                                },
                                "minimize_window": {
                                    "type": "boolean",
                                    "description": "是否自动最小化窗口",
                                    "default": True
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "get_controller_info",
                        "description": "获取控制器信息和支持的功能",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        if tool_name == "launch_netease_music":
            result = launch_netease_music(**arguments)
        elif tool_name == "control_playback":
            result = control_playback(**arguments)
        elif tool_name == "search_and_play":
            result = search_and_play(**arguments)
        elif tool_name == "get_controller_info":
            result = get_controller_info()
        else:
            result = {
                "success": False,
                "error": f"未知的工具: {tool_name}"
            }
        
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            }
        }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32601,
                "message": f"未知的方法: {method}"
            }
        }

def main():
    """主函数 - 简单的 MCP 服务器"""
    try:
        print("🎵 网易云音乐 MCP 控制器 - 简化版", file=sys.stderr)
        print(f"当前平台: {get_platform()}", file=sys.stderr)
        print("支持的功能:", file=sys.stderr)
        print("- URL scheme 启动 (orpheus://)", file=sys.stderr)
        print("- 全局快捷键控制", file=sys.stderr)
    except UnicodeEncodeError:
        print("网易云音乐 MCP 控制器 - 简化版", file=sys.stderr)
        print("当前平台: Windows", file=sys.stderr)
    
    # 简单的 MCP 协议处理
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = handle_mcp_request(request)
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"内部错误: {str(e)}"
                }
            }
            print(json.dumps(error_response, ensure_ascii=False))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
