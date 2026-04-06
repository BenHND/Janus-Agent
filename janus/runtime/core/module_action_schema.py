"""
Module and Action Schema Definition - TICKET 003

This module defines the COMPLETE and STRICT schema for all modules and their valid actions.
This is the single source of truth for what actions are allowed in Janus.

The Reasoner MUST only generate actions from this schema.
The Validator MUST reject any action not defined here.

Format Version: V3
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """
    Risk level for actions - used for human-in-the-loop confirmation (SAFETY-001).
    
    This is the SINGLE SOURCE OF TRUTH for action risk classification.
    
    - LOW: Safe actions that don't modify state (read, view, search)
    - MEDIUM: Actions that modify state but are reversible (click, type, navigate)
    - HIGH: Dangerous actions that require confirmation (delete, send, execute)
    - CRITICAL: System-level or irreversible actions requiring strict confirmation
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModuleName(Enum):
    """
    The 8 universal modules in Janus (TICKET 003).
    
    Every action in Janus MUST be routed through one of these modules.
    """
    SYSTEM = "system"
    BROWSER = "browser"
    MESSAGING = "messaging"
    CRM = "crm"
    FILES = "files"
    UI = "ui"
    CODE = "code"
    LLM = "llm"


@dataclass
class ActionParameter:
    """Definition of an action parameter"""
    name: str
    type: str  # "string", "int", "float", "bool", "dict", "list"
    required: bool
    description: str
    default: Optional[Any] = None
    
    def validate(self, value: Any) -> bool:
        """Validate parameter value against type"""
        if value is None:
            return not self.required
        
        # Type validation
        type_map = {
            "string": str,
            "int": int,
            "float": (int, float),
            "bool": bool,
            "dict": dict,
            "list": list,
        }
        
        expected_type = type_map.get(self.type)
        if expected_type and not isinstance(value, expected_type):
            return False
        
        return True


@dataclass
class ActionDefinition:
    """Definition of a valid action within a module"""
    name: str
    description: str
    parameters: List[ActionParameter] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)  # Alternative names for the action
    risk_level: RiskLevel = RiskLevel.LOW  # Risk level for confirmation (TICKET-SEC-001)
    
    def get_required_params(self) -> List[str]:
        """Get list of required parameter names"""
        return [p.name for p in self.parameters if p.required]
    
    def get_optional_params(self) -> List[str]:
        """Get list of optional parameter names"""
        return [p.name for p in self.parameters if not p.required]
    
    def validate_params(self, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate action arguments against parameter definitions.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in args:
                return False, f"Missing required parameter: {param.name}"
            
            # Validate type if parameter provided
            if param.name in args:
                if not param.validate(args[param.name]):
                    return False, f"Invalid type for parameter '{param.name}': expected {param.type}, got {type(args[param.name]).__name__}"
        
        # Check for unknown parameters (optional - can be strict or lenient)
        known_params = {p.name for p in self.parameters}
        unknown = set(args.keys()) - known_params
        if unknown:
            # For now, just warn but allow (can be made strict later)
            pass
        
        return True, None


@dataclass
class ModuleDefinition:
    """Definition of a module with all its valid actions"""
    name: ModuleName
    description: str
    actions: List[ActionDefinition] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)  # Alternative names for the module
    
    def get_action(self, action_name: str) -> Optional[ActionDefinition]:
        """Get action definition by name or alias"""
        # Try exact match first
        for action in self.actions:
            if action.name == action_name:
                return action
        
        # Try aliases
        for action in self.actions:
            if action_name in action.aliases:
                return action
        
        return None
    
    def get_action_names(self) -> List[str]:
        """Get list of all valid action names"""
        return [action.name for action in self.actions]
    
    def has_action(self, action_name: str) -> bool:
        """Check if module supports an action"""
        return self.get_action(action_name) is not None


# =============================================================================
# MODULE SCHEMAS - The definitive list of modules and their actions
# =============================================================================

SYSTEM_MODULE = ModuleDefinition(
    name=ModuleName.SYSTEM,
    description="Actions système macOS",
    actions=[
        ActionDefinition(
            name="open_application",
            description="Ouvrir une application",
            parameters=[
                ActionParameter("app_name", "string", True, "Nom de l'application (Safari, Chrome, VSCode, etc.)")
            ],
            examples=[
                '{"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}',
                '{"module": "system", "action": "open_application", "args": {"app_name": "Chrome"}}',
            ],
            aliases=["open_app", "launch", "launch_app"]
        ),
        ActionDefinition(
            name="close_application",
            description="Fermer une application",
            parameters=[
                ActionParameter("app_name", "string", True, "Nom de l'application à fermer")
            ],
            examples=[
                '{"module": "system", "action": "close_application", "args": {"app_name": "Safari"}}'
            ],
            aliases=["close_app", "quit_app"],
            risk_level=RiskLevel.MEDIUM  # Closing apps is moderately risky
        ),
        ActionDefinition(
            name="switch_application",
            description="Basculer vers une application",
            parameters=[
                ActionParameter("app_name", "string", True, "Nom de l'application cible")
            ],
            examples=[
                '{"module": "system", "action": "switch_application", "args": {"app_name": "Chrome"}}'
            ],
            aliases=["switch_app", "focus_app", "activate_app"]
        ),
        ActionDefinition(
            name="get_active_app",
            description="Obtenir l'application active/frontale",
            parameters=[],
            examples=[
                '{"module": "system", "action": "get_active_app", "args": {}}'
            ],
            aliases=["get_frontmost_app", "active_app"]
        ),
        ActionDefinition(
            name="open_deep_link",
            description="Ouvrir un lien profond vers une application SaaS (Zoom, Notion, Spotify, etc.) - TICKET-BIZ-003",
            parameters=[
                ActionParameter("app", "string", True, "Nom de l'application (zoom, notion, spotify, slack, teams, jira, trello, figma, discord, github, vscode, calendar)"),
                ActionParameter("args", "dict", True, "Arguments pour construire l'URL (ex: {\"id\": \"123-456\"} pour Zoom)"),
                ActionParameter("use_web_fallback", "bool", False, "Utiliser l'URL web au lieu du schéma natif", default=False)
            ],
            examples=[
                '{"module": "system", "action": "open_deep_link", "args": {"app": "zoom", "args": {"id": "123-456-789"}}}',
                '{"module": "system", "action": "open_deep_link", "args": {"app": "spotify", "args": {"type": "track", "id": "3n3Ppam7vgaVa1iaRUc9Lp"}}}',
                '{"module": "system", "action": "open_deep_link", "args": {"app": "notion", "args": {"slug": "My-Page-123abc"}}}',
                '{"module": "system", "action": "open_deep_link", "args": {"app": "slack", "args": {"team_id": "T123ABC", "channel_id": "C456DEF"}}}',
            ],
            aliases=["deep_link", "open_url_scheme"],
            risk_level=RiskLevel.LOW  # Opening deep links is generally safe
        ),
        ActionDefinition(
            name="keystroke",
            description="Exécuter une frappe de touche avec modificateurs optionnels",
            parameters=[
                ActionParameter("keys", "string", True, "Touches à presser (ex: 'return', 'command l', 'command shift t')")
            ],
            examples=[
                '{"module": "system", "action": "keystroke", "args": {"keys": "return"}}',
                '{"module": "system", "action": "keystroke", "args": {"keys": "command l"}}',
            ],
            aliases=["send_keys", "press_keys"]
        ),
        ActionDefinition(
            name="shortcut",
            description="Exécuter un raccourci nommé",
            parameters=[
                ActionParameter("name", "string", True, "Nom du raccourci (copy, paste, cut, undo, redo, save, find, etc.)")
            ],
            examples=[
                '{"module": "system", "action": "shortcut", "args": {"name": "copy"}}',
                '{"module": "system", "action": "shortcut", "args": {"name": "paste"}}',
            ],
            aliases=["keyboard_shortcut"]
        ),
        ActionDefinition(
            name="type",
            description="Saisir du texte",
            parameters=[
                ActionParameter("text", "string", True, "Texte à saisir")
            ],
            examples=[
                '{"module": "system", "action": "type", "args": {"text": "Hello world"}}'
            ],
            aliases=["type_text", "input_text"]
        ),
    ]
)

BROWSER_MODULE = ModuleDefinition(
    name=ModuleName.BROWSER,
    description="Navigation web (Safari, Chrome, Edge, Firefox)",
    actions=[
        ActionDefinition(
            name="open_url",
            description="Ouvrir une URL",
            parameters=[
                ActionParameter("url", "string", True, "URL à ouvrir (complète avec https://)")
            ],
            examples=[
                '{"module": "browser", "action": "open_url", "args": {"url": "https://example.com"}}',
                '{"module": "browser", "action": "open_url", "args": {"url": "https://github.com/BenHND/Janus"}}',
            ],
            aliases=["navigate", "goto", "go_to_url"]
        ),
        ActionDefinition(
            name="navigate_back",
            description="Page précédente",
            parameters=[],
            examples=[
                '{"module": "browser", "action": "navigate_back", "args": {}}'
            ],
            aliases=["back", "go_back"]
        ),
        ActionDefinition(
            name="navigate_forward",
            description="Page suivante",
            parameters=[],
            examples=[
                '{"module": "browser", "action": "navigate_forward", "args": {}}'
            ],
            aliases=["forward", "go_forward"]
        ),
        ActionDefinition(
            name="refresh",
            description="Actualiser la page",
            parameters=[],
            examples=[
                '{"module": "browser", "action": "refresh", "args": {}}'
            ],
            aliases=["reload", "refresh_page"]
        ),
        ActionDefinition(
            name="open_tab",
            description="Nouvel onglet",
            parameters=[
                ActionParameter("url", "string", False, "URL optionnelle à ouvrir dans le nouvel onglet", default=None)
            ],
            examples=[
                '{"module": "browser", "action": "open_tab", "args": {}}',
                '{"module": "browser", "action": "open_tab", "args": {"url": "https://example.com"}}',
            ],
            aliases=["new_tab", "create_tab"]
        ),
        ActionDefinition(
            name="close_tab",
            description="Fermer l'onglet courant",
            parameters=[],
            examples=[
                '{"module": "browser", "action": "close_tab", "args": {}}'
            ],
            aliases=["close_current_tab"]
        ),
        ActionDefinition(
            name="search",
            description="Rechercher sur le web (moteur générique)",
            parameters=[
                ActionParameter("query", "string", True, "Terme de recherche"),
                ActionParameter("engine", "string", False, "Moteur de recherche (duckduckgo par défaut)", default="duckduckgo")
            ],
            examples=[
                '{"module": "browser", "action": "search", "args": {"query": "Python tutorials"}}',
                '{"module": "browser", "action": "search", "args": {"query": "AI news", "engine": "duckduckgo"}}',
            ],
            aliases=["search_web"]
        ),
        ActionDefinition(
            name="extract_text",
            description="Extraire le texte de la page",
            parameters=[],
            examples=[
                '{"module": "browser", "action": "extract_text", "args": {}}'
            ],
            aliases=["get_text", "extract_page_text", "get_page_content"]
        ),
        ActionDefinition(
            name="click",
            description="Cliquer sur un élément dans la page (via sélecteur CSS)",
            parameters=[
                ActionParameter("selector", "string", True, "Sélecteur CSS de l'élément")
            ],
            examples=[
                '{"module": "browser", "action": "click", "args": {"selector": "#submit-button"}}'
            ],
            aliases=["click_element"]
        ),
        ActionDefinition(
            name="type_text",
            description="Saisir du texte dans le navigateur",
            parameters=[
                ActionParameter("text", "string", True, "Texte à saisir")
            ],
            examples=[
                '{"module": "browser", "action": "type_text", "args": {"text": "Hello"}}'
            ],
            aliases=["input_text", "enter_text"]
        ),
        ActionDefinition(
            name="press_key",
            description="Appuyer sur une touche",
            parameters=[
                ActionParameter("keys", "string", True, "Touches à presser (ex: 'enter', 'escape', 'tab')")
            ],
            examples=[
                '{"module": "browser", "action": "press_key", "args": {"keys": "enter"}}'
            ],
            aliases=["send_key", "keystroke"]
        ),
    ]
)

MESSAGING_MODULE = ModuleDefinition(
    name=ModuleName.MESSAGING,
    description="Communication (Teams, Slack, Messages)",
    actions=[
        ActionDefinition(
            name="send_message",
            description="Envoyer un message",
            parameters=[
                ActionParameter("message", "string", True, "Contenu du message"),
                ActionParameter("recipient", "string", False, "Destinataire (optionnel si conversation ouverte)", default=None),
                ActionParameter("thread_id", "string", False, "ID du fil de conversation", default=None)
            ],
            examples=[
                '{"module": "messaging", "action": "send_message", "args": {"message": "Bonjour"}}',
                '{"module": "messaging", "action": "send_message", "args": {"message": "Meeting at 3pm", "recipient": "John"}}',
            ],
            aliases=["send", "post_message"],
            risk_level=RiskLevel.HIGH  # Sending messages is high risk
        ),
        ActionDefinition(
            name="open_thread",
            description="Ouvrir une conversation",
            parameters=[
                ActionParameter("name", "string", False, "Nom du contact ou canal", default=None),
                ActionParameter("thread_id", "string", False, "ID du fil", default=None)
            ],
            examples=[
                '{"module": "messaging", "action": "open_thread", "args": {"name": "General"}}',
                '{"module": "messaging", "action": "open_thread", "args": {"thread_id": "12345"}}',
            ],
            aliases=["open_conversation", "open_chat"]
        ),
        ActionDefinition(
            name="search_messages",
            description="Rechercher dans les messages",
            parameters=[
                ActionParameter("query", "string", True, "Terme de recherche")
            ],
            examples=[
                '{"module": "messaging", "action": "search_messages", "args": {"query": "meeting notes"}}'
            ],
            aliases=["search", "find_messages"]
        ),
        ActionDefinition(
            name="read_channel_history",
            description="Lire l'historique d'un canal",
            parameters=[
                ActionParameter("platform", "string", True, "Plateforme (slack, teams)"),
                ActionParameter("channel", "string", True, "Nom ou ID du canal"),
                ActionParameter("limit", "int", False, "Nombre de messages à récupérer", default=50)
            ],
            examples=[
                '{"module": "messaging", "action": "read_channel_history", "args": {"platform": "slack", "channel": "general"}}'
            ],
            aliases=["get_history", "fetch_messages"]
        ),
        ActionDefinition(
            name="summarize_thread",
            description="Résumer une conversation",
            parameters=[
                ActionParameter("platform", "string", True, "Plateforme (slack, teams)"),
                ActionParameter("channel", "string", True, "Nom ou ID du canal"),
                ActionParameter("since_time", "string", False, "Depuis quand (ISO timestamp)", default=None)
            ],
            examples=[
                '{"module": "messaging", "action": "summarize_thread", "args": {"platform": "slack", "channel": "general"}}'
            ],
            aliases=["summarize_conversation"]
        ),
        ActionDefinition(
            name="join_call",
            description="Rejoindre un appel",
            parameters=[
                ActionParameter("platform", "string", True, "Plateforme (teams, slack)"),
                ActionParameter("call_id", "string", False, "ID de l'appel", default=None)
            ],
            examples=[
                '{"module": "messaging", "action": "join_call", "args": {"platform": "teams"}}'
            ],
            aliases=["join_meeting"]
        ),
        ActionDefinition(
            name="leave_call",
            description="Quitter un appel",
            parameters=[],
            examples=[
                '{"module": "messaging", "action": "leave_call", "args": {}}'
            ],
            aliases=["end_call", "quit_call"]
        ),
    ]
)

CRM_MODULE = ModuleDefinition(
    name=ModuleName.CRM,
    description="Gestion CRM (Salesforce, HubSpot)",
    actions=[
        ActionDefinition(
            name="open_record",
            description="Ouvrir un enregistrement",
            parameters=[
                ActionParameter("record_id", "string", True, "ID de l'enregistrement"),
                ActionParameter("record_type", "string", False, "Type (account, contact, opportunity)", default="account")
            ],
            examples=[
                '{"module": "crm", "action": "open_record", "args": {"record_id": "001xyz", "record_type": "account"}}'
            ],
            aliases=["view_record", "show_record"]
        ),
        ActionDefinition(
            name="search_records",
            description="Rechercher des enregistrements",
            parameters=[
                ActionParameter("query", "string", True, "Terme de recherche"),
                ActionParameter("record_type", "string", False, "Type d'enregistrement", default=None)
            ],
            examples=[
                '{"module": "crm", "action": "search_records", "args": {"query": "Acme Corp"}}'
            ],
            aliases=["search", "find_records"]
        ),
        ActionDefinition(
            name="update_field",
            description="Mettre à jour un champ",
            parameters=[
                ActionParameter("field_name", "string", True, "Nom du champ"),
                ActionParameter("value", "string", True, "Nouvelle valeur"),
                ActionParameter("record_id", "string", False, "ID de l'enregistrement (optionnel si déjà ouvert)", default=None)
            ],
            examples=[
                '{"module": "crm", "action": "update_field", "args": {"field_name": "Status", "value": "Closed Won"}}'
            ],
            aliases=["set_field", "modify_field"],
            risk_level=RiskLevel.HIGH  # Updating CRM fields is high risk
        ),
        ActionDefinition(
            name="search_contact",
            description="Rechercher un contact",
            parameters=[
                ActionParameter("name", "string", False, "Nom du contact", default=None),
                ActionParameter("email", "string", False, "Email du contact", default=None)
            ],
            examples=[
                '{"module": "crm", "action": "search_contact", "args": {"name": "John Doe"}}'
            ],
            aliases=["find_contact", "get_contact"]
        ),
        ActionDefinition(
            name="search_opportunities",
            description="Rechercher des opportunités",
            parameters=[
                ActionParameter("query", "string", True, "Terme de recherche")
            ],
            examples=[
                '{"module": "crm", "action": "search_opportunities", "args": {"query": "Acme Deal"}}'
            ],
            aliases=["find_opportunities", "get_opportunity"]
        ),
        ActionDefinition(
            name="get_account",
            description="Récupérer les détails d'un compte",
            parameters=[
                ActionParameter("account_id", "string", False, "ID du compte", default=None),
                ActionParameter("name", "string", False, "Nom du compte", default=None)
            ],
            examples=[
                '{"module": "crm", "action": "get_account", "args": {"name": "Acme Corp"}}'
            ],
            aliases=["fetch_account"]
        ),
        ActionDefinition(
            name="generate_contact_url",
            description="Générer l'URL d'un contact",
            parameters=[
                ActionParameter("contact_id", "string", True, "ID du contact")
            ],
            examples=[
                '{"module": "crm", "action": "generate_contact_url", "args": {"contact_id": "003xyz"}}'
            ],
            aliases=["contact_url"]
        ),
        ActionDefinition(
            name="generate_opportunity_url",
            description="Générer l'URL d'une opportunité",
            parameters=[
                ActionParameter("opportunity_id", "string", True, "ID de l'opportunité")
            ],
            examples=[
                '{"module": "crm", "action": "generate_opportunity_url", "args": {"opportunity_id": "006xyz"}}'
            ],
            aliases=["opportunity_url"]
        ),
    ]
)

FILES_MODULE = ModuleDefinition(
    name=ModuleName.FILES,
    description="Gestion de fichiers (Finder)",
    actions=[
        ActionDefinition(
            name="open_file",
            description="Ouvrir un fichier",
            parameters=[
                ActionParameter("path", "string", True, "Chemin du fichier"),
                ActionParameter("app", "string", False, "Application pour ouvrir le fichier", default=None)
            ],
            examples=[
                '{"module": "files", "action": "open_file", "args": {"path": "/Users/me/document.pdf"}}',
                '{"module": "files", "action": "open_file", "args": {"path": "/Users/me/code.py", "app": "VSCode"}}',
            ],
            aliases=["open"]
        ),
        ActionDefinition(
            name="save_file",
            description="Sauvegarder un fichier",
            parameters=[
                ActionParameter("path", "string", False, "Chemin de destination (optionnel)", default=None),
                ActionParameter("content", "string", False, "Contenu du fichier", default=None)
            ],
            examples=[
                '{"module": "files", "action": "save_file", "args": {}}',
                '{"module": "files", "action": "save_file", "args": {"path": "/Users/me/new_file.txt", "content": "Hello world"}}',
            ],
            aliases=["save"]
        ),
        ActionDefinition(
            name="search_files",
            description="Rechercher des fichiers",
            parameters=[
                ActionParameter("query", "string", True, "Terme de recherche"),
                ActionParameter("directory", "string", False, "Répertoire de recherche", default=None)
            ],
            examples=[
                '{"module": "files", "action": "search_files", "args": {"query": "report.pdf"}}',
                '{"module": "files", "action": "search_files", "args": {"query": "*.py", "directory": "/Users/me/projects"}}',
            ],
            aliases=["search", "find_files", "find"]
        ),
        ActionDefinition(
            name="create_folder",
            description="Créer un dossier",
            parameters=[
                ActionParameter("path", "string", True, "Chemin du nouveau dossier")
            ],
            examples=[
                '{"module": "files", "action": "create_folder", "args": {"path": "/Users/me/new_project"}}'
            ],
            aliases=["mkdir", "create_directory"],
            risk_level=RiskLevel.MEDIUM  # Creating folders is moderately risky
        ),
        ActionDefinition(
            name="delete_file",
            description="Supprimer un fichier",
            parameters=[
                ActionParameter("path", "string", True, "Chemin du fichier à supprimer")
            ],
            examples=[
                '{"module": "files", "action": "delete_file", "args": {"path": "/Users/me/document.pdf"}}'
            ],
            aliases=["remove_file", "delete", "remove"],
            risk_level=RiskLevel.HIGH  # Deleting files is high risk - requires confirmation
        ),
        ActionDefinition(
            name="read_file",
            description="Lire le contenu d'un fichier",
            parameters=[
                ActionParameter("path", "string", True, "Chemin du fichier à lire")
            ],
            examples=[
                '{"module": "files", "action": "read_file", "args": {"path": "/Users/me/document.txt"}}'
            ],
            aliases=["get_file_content"]
        ),
        ActionDefinition(
            name="write_file",
            description="Écrire dans un fichier",
            parameters=[
                ActionParameter("path", "string", True, "Chemin du fichier"),
                ActionParameter("content", "string", True, "Contenu à écrire")
            ],
            examples=[
                '{"module": "files", "action": "write_file", "args": {"path": "/Users/me/doc.txt", "content": "Hello"}}'
            ],
            aliases=["save_to_file"],
            risk_level=RiskLevel.MEDIUM
        ),
        ActionDefinition(
            name="copy_file",
            description="Copier un fichier",
            parameters=[
                ActionParameter("source", "string", True, "Chemin source"),
                ActionParameter("destination", "string", True, "Chemin destination")
            ],
            examples=[
                '{"module": "files", "action": "copy_file", "args": {"source": "/path/file.txt", "destination": "/path/copy.txt"}}'
            ],
            aliases=["cp"],
            risk_level=RiskLevel.MEDIUM
        ),
        ActionDefinition(
            name="move_file",
            description="Déplacer un fichier",
            parameters=[
                ActionParameter("source", "string", True, "Chemin source"),
                ActionParameter("destination", "string", True, "Chemin destination")
            ],
            examples=[
                '{"module": "files", "action": "move_file", "args": {"source": "/old/file.txt", "destination": "/new/file.txt"}}'
            ],
            aliases=["mv", "rename"],
            risk_level=RiskLevel.MEDIUM
        ),
        ActionDefinition(
            name="list_directory",
            description="Lister le contenu d'un répertoire",
            parameters=[
                ActionParameter("path", "string", True, "Chemin du répertoire")
            ],
            examples=[
                '{"module": "files", "action": "list_directory", "args": {"path": "/Users/me/Documents"}}'
            ],
            aliases=["ls", "list_dir", "dir"]
        ),
        ActionDefinition(
            name="open_path",
            description="Ouvrir un fichier ou dossier dans le Finder/Explorateur",
            parameters=[
                ActionParameter("path", "string", True, "Chemin à ouvrir")
            ],
            examples=[
                '{"module": "files", "action": "open_path", "args": {"path": "/Users/me/Documents"}}'
            ],
            aliases=["reveal", "show_in_finder"]
        ),
    ]
)

UI_MODULE = ModuleDefinition(
    name=ModuleName.UI,
    description="Actions interface utilisateur",
    actions=[
        ActionDefinition(
            name="click",
            description="Cliquer sur un élément (utilise l'accessibilité si disponible, sinon vision)",
            parameters=[
                ActionParameter("target", "string", False, "Description ou texte de l'élément", default=None),
                ActionParameter("role", "string", False, "Rôle de l'élément pour l'accessibilité (button, link, text_field, checkbox, etc.)", default=None),
                ActionParameter("x", "int", False, "Position X (optionnel)", default=None),
                ActionParameter("y", "int", False, "Position Y (optionnel)", default=None),
                ActionParameter("method", "string", False, "Méthode (accessibility, vision, position)", default="accessibility")
            ],
            examples=[
                '{"module": "ui", "action": "click", "args": {"target": "Envoyer", "role": "button"}}',
                '{"module": "ui", "action": "click", "args": {"target": "OK"}}',
                '{"module": "ui", "action": "click", "args": {"x": 100, "y": 200, "method": "position"}}',
            ],
            aliases=["click_on"],
            risk_level=RiskLevel.MEDIUM  # Clicking can trigger actions
        ),
        ActionDefinition(
            name="copy",
            description="Copier",
            parameters=[],
            examples=[
                '{"module": "ui", "action": "copy", "args": {}}'
            ],
            aliases=["copy_selection"]
        ),
        ActionDefinition(
            name="paste",
            description="Coller",
            parameters=[],
            examples=[
                '{"module": "ui", "action": "paste", "args": {}}'
            ],
            aliases=["paste_clipboard"]
        ),
        ActionDefinition(
            name="type",
            description="Saisir du texte",
            parameters=[
                ActionParameter("text", "string", True, "Texte à saisir")
            ],
            examples=[
                '{"module": "ui", "action": "type", "args": {"text": "Hello world"}}'
            ],
            aliases=["type_text", "input", "enter_text"]
        ),
        ActionDefinition(
            name="highlight_area",
            description="Mettre en surbrillance une zone de l'écran",
            parameters=[
                ActionParameter("x", "int", True, "Position X"),
                ActionParameter("y", "int", True, "Position Y"),
                ActionParameter("width", "int", True, "Largeur"),
                ActionParameter("height", "int", True, "Hauteur")
            ],
            examples=[
                '{"module": "ui", "action": "highlight_area", "args": {"x": 100, "y": 100, "width": 200, "height": 50}}'
            ],
            aliases=["highlight"]
        ),
        ActionDefinition(
            name="overlay",
            description="Afficher un overlay sur l'écran",
            parameters=[
                ActionParameter("message", "string", True, "Message à afficher")
            ],
            examples=[
                '{"module": "ui", "action": "overlay", "args": {"message": "Processing..."}}'
            ],
            aliases=["show_overlay"]
        ),
        ActionDefinition(
            name="notify",
            description="Afficher une notification",
            parameters=[
                ActionParameter("title", "string", True, "Titre de la notification"),
                ActionParameter("message", "string", True, "Message de la notification")
            ],
            examples=[
                '{"module": "ui", "action": "notify", "args": {"title": "Task Complete", "message": "Action executed successfully"}}'
            ],
            aliases=["notification", "alert"]
        ),
    ]
)

CODE_MODULE = ModuleDefinition(
    name=ModuleName.CODE,
    description="Édition de code (VSCode, Cursor)",
    actions=[
        ActionDefinition(
            name="open_file",
            description="Ouvrir un fichier de code",
            parameters=[
                ActionParameter("path", "string", True, "Chemin du fichier")
            ],
            examples=[
                '{"module": "code", "action": "open_file", "args": {"path": "/Users/me/project/main.py"}}'
            ],
            aliases=["open"]
        ),
        ActionDefinition(
            name="goto_line",
            description="Aller à la ligne",
            parameters=[
                ActionParameter("line", "int", True, "Numéro de ligne")
            ],
            examples=[
                '{"module": "code", "action": "goto_line", "args": {"line": 42}}'
            ],
            aliases=["go_to_line", "jump_to_line"]
        ),
        ActionDefinition(
            name="find_text",
            description="Rechercher du texte",
            parameters=[
                ActionParameter("query", "string", True, "Texte à rechercher")
            ],
            examples=[
                '{"module": "code", "action": "find_text", "args": {"query": "function main"}}'
            ],
            aliases=["search", "find"]
        ),
        ActionDefinition(
            name="save_file",
            description="Sauvegarder",
            parameters=[],
            examples=[
                '{"module": "code", "action": "save_file", "args": {}}'
            ],
            aliases=["save"]
        ),
        ActionDefinition(
            name="paste",
            description="Coller le contenu du presse-papiers",
            parameters=[],
            examples=[
                '{"module": "code", "action": "paste", "args": {}}'
            ],
            aliases=["paste_clipboard"]
        ),
    ]
)

LLM_MODULE = ModuleDefinition(
    name=ModuleName.LLM,
    description="Actions IA natives",
    actions=[
        ActionDefinition(
            name="summarize",
            description="Résumer",
            parameters=[
                ActionParameter("input", "string", False, "Texte à résumer (ou input_from)", default=None),
                ActionParameter("input_from", "string", False, "Référence à une sortie précédente", default=None),
                ActionParameter("max_length", "int", False, "Longueur maximale du résumé", default=None)
            ],
            examples=[
                '{"module": "llm", "action": "summarize", "args": {"input_from": "last_output"}}',
                '{"module": "llm", "action": "summarize", "args": {"input": "Long text..."}}',
            ],
            aliases=["summary", "summarise"]
        ),
        ActionDefinition(
            name="rewrite",
            description="Réécrire",
            parameters=[
                ActionParameter("input", "string", False, "Texte à réécrire", default=None),
                ActionParameter("input_from", "string", False, "Référence à une sortie précédente", default=None),
                ActionParameter("style", "string", False, "Style de réécriture (formal, casual, professional)", default=None)
            ],
            examples=[
                '{"module": "llm", "action": "rewrite", "args": {"input": "Text to rewrite", "style": "professional"}}'
            ],
            aliases=["rephrase", "reformulate"]
        ),
        ActionDefinition(
            name="extract_keywords",
            description="Extraire mots-clés",
            parameters=[
                ActionParameter("input", "string", False, "Texte source", default=None),
                ActionParameter("input_from", "string", False, "Référence à une sortie précédente", default=None),
                ActionParameter("count", "int", False, "Nombre de mots-clés", default=5)
            ],
            examples=[
                '{"module": "llm", "action": "extract_keywords", "args": {"input_from": "last_output", "count": 5}}'
            ],
            aliases=["keywords", "extract_tags"]
        ),
        ActionDefinition(
            name="analyze_error",
            description="Analyser une erreur",
            parameters=[
                ActionParameter("error", "string", True, "Message d'erreur"),
                ActionParameter("context", "string", False, "Contexte de l'erreur", default=None)
            ],
            examples=[
                '{"module": "llm", "action": "analyze_error", "args": {"error": "TypeError: cannot concatenate str and int"}}'
            ],
            aliases=["analyze", "explain_error", "analyse"]
        ),
        ActionDefinition(
            name="answer_question",
            description="Répondre à une question",
            parameters=[
                ActionParameter("question", "string", True, "Question à poser"),
                ActionParameter("context", "string", False, "Contexte pour la réponse", default=None)
            ],
            examples=[
                '{"module": "llm", "action": "answer_question", "args": {"question": "What is the meaning of life?"}}'
            ],
            aliases=["ask", "question"]
        ),
    ]
)

# Registry of all modules
ALL_MODULES: Dict[str, ModuleDefinition] = {
    ModuleName.SYSTEM.value: SYSTEM_MODULE,
    ModuleName.BROWSER.value: BROWSER_MODULE,
    ModuleName.MESSAGING.value: MESSAGING_MODULE,
    ModuleName.CRM.value: CRM_MODULE,
    ModuleName.FILES.value: FILES_MODULE,
    ModuleName.UI.value: UI_MODULE,
    ModuleName.CODE.value: CODE_MODULE,
    ModuleName.LLM.value: LLM_MODULE,
}


# =============================================================================
# SCHEMA QUERY AND VALIDATION FUNCTIONS
# =============================================================================

def get_module(module_name: str) -> Optional[ModuleDefinition]:
    """Get module definition by name"""
    return ALL_MODULES.get(module_name)


def get_all_module_names() -> List[str]:
    """Get list of all valid module names"""
    return list(ALL_MODULES.keys())


def get_all_actions_for_module(module_name: str) -> List[str]:
    """Get all valid action names for a module"""
    module = get_module(module_name)
    return module.get_action_names() if module else []


def is_valid_module(module_name: str) -> bool:
    """Check if module name is valid"""
    return module_name in ALL_MODULES


def is_valid_action(module_name: str, action_name: str) -> bool:
    """Check if action is valid for the module"""
    module = get_module(module_name)
    return module.has_action(action_name) if module else False


def validate_action_step(step: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a complete action step (module, action, args).
    
    TICKET-P0: Enhanced to validate against both module_action_schema and agent decorators.
    
    Args:
        step: Step dictionary with "module", "action", "args" keys
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required keys
    if "module" not in step:
        return False, "Missing 'module' field in step"
    
    if "action" not in step:
        return False, "Missing 'action' field in step"
    
    module_name = step["module"]
    action_name = step["action"]
    args = step.get("args", {})
    
    # Validate module exists in schema
    if not is_valid_module(module_name):
        valid_modules = get_all_module_names()
        return False, f"Invalid module '{module_name}'. Valid modules: {', '.join(valid_modules)}"
    
    # Validate action exists for module in schema
    if not is_valid_action(module_name, action_name):
        valid_actions = get_all_actions_for_module(module_name)
        return False, f"Invalid action '{action_name}' for module '{module_name}'. Valid actions: {', '.join(valid_actions)}"
    
    # Validate action parameters via schema
    module = get_module(module_name)
    action_def = module.get_action(action_name)
    
    if action_def:
        is_valid, error = action_def.validate_params(args)
        if not is_valid:
            return False, f"Parameter validation failed for {module_name}.{action_name}: {error}"
    
    return True, None


def validate_action_step_with_agents(step: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate action step against registered agent decorators.
    
    TICKET-P0: New unified validation that checks against @agent_action decorators.
    This provides more accurate validation when agents are registered.
    
    Args:
        step: Step dictionary with "module", "action", "args" keys
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from janus.runtime.core.agent_registry import get_global_agent_registry
        from janus.capabilities.agents.decorators import list_agent_actions
    except ImportError:
        # Fall back to schema validation if agents not available
        return validate_action_step(step)
    
    # Check required keys
    if "module" not in step:
        return False, "Missing 'module' field in step"
    
    if "action" not in step:
        return False, "Missing 'action' field in step"
    
    module_name = step["module"]
    action_name = step["action"]
    args = step.get("args", {})
    
    # Get the agent for this module
    registry = get_global_agent_registry()
    agent = registry.get_agent(module_name)
    
    if not agent:
        # No agent registered - fall back to schema validation
        return validate_action_step(step)
    
    # Get all actions for this agent
    actions = list_agent_actions(agent)
    
    # Find the action metadata
    action_metadata = None
    for metadata in actions:
        if metadata.name == action_name:
            action_metadata = metadata
            break
    
    if not action_metadata:
        # Action not found in agent decorators
        action_names = [m.name for m in actions]
        return False, f"Invalid action '{action_name}' for agent '{module_name}'. Valid actions: {', '.join(action_names)}"
    
    # Validate required arguments
    missing_args = [arg for arg in action_metadata.required_args if arg not in args]
    if missing_args:
        return False, f"Missing required arguments for {module_name}.{action_name}: {', '.join(missing_args)}"
    
    # Validate no unexpected arguments (warning only - can be made strict)
    known_args = set(action_metadata.required_args) | set(action_metadata.optional_args.keys())
    unexpected_args = set(args.keys()) - known_args
    if unexpected_args:
        # For now just log warning, don't fail validation
        logger.warning(
            f"Unexpected arguments for {module_name}.{action_name}: {', '.join(unexpected_args)}. "
            f"Expected: {', '.join(known_args)}"
        )
    
    return True, None


def validate_action_plan(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a complete action plan with multiple steps.
    
    Args:
        plan: Plan dictionary with "steps" array
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if "steps" not in plan:
        return False, ["Missing 'steps' field in plan"]
    
    steps = plan["steps"]
    if not isinstance(steps, list):
        return False, ["'steps' must be an array"]
    
    errors = []
    for i, step in enumerate(steps):
        is_valid, error = validate_action_step(step)
        if not is_valid:
            errors.append(f"Step {i}: {error}")
    
    return len(errors) == 0, errors


def get_schema_summary() -> str:
    """
    Get a human-readable summary of the entire schema.
    
    Useful for:
    - Documentation
    - LLM prompts
    - Debug output
    """
    summary = ["# Module and Action Schema", ""]
    
    for module_name, module in ALL_MODULES.items():
        summary.append(f"## {module_name} - {module.description}")
        summary.append("")
        
        for action in module.actions:
            params_str = ", ".join([
                f"{p.name}:{p.type}{'*' if p.required else ''}"
                for p in action.parameters
            ])
            summary.append(f"  - **{action.name}**({params_str}): {action.description}")
            
            if action.aliases:
                summary.append(f"    Aliases: {', '.join(action.aliases)}")
        
        summary.append("")
    
    return "\n".join(summary)


def auto_correct_action(module_name: str, action_name: str) -> Optional[str]:
    """
    Try to auto-correct an invalid action name using aliases.
    
    Args:
        module_name: Module name
        action_name: Potentially incorrect action name
    
    Returns:
        Corrected action name (canonical name) or None if no correction found
    """
    module = get_module(module_name)
    if not module:
        return None
    
    # Check if already valid - find the canonical name
    for action_def in module.actions:
        # Exact match on canonical name
        if action_def.name == action_name:
            return action_name
        
        # Match on alias - return canonical name
        if action_name in action_def.aliases:
            return action_def.name
    
    # Try fuzzy matching (simple case-insensitive)
    action_name_lower = action_name.lower()
    for action_def in module.actions:
        if action_def.name.lower() == action_name_lower:
            return action_def.name
        
        # Check aliases case-insensitive
        for alias in action_def.aliases:
            if alias.lower() == action_name_lower:
                return action_def.name
    
    return None


def auto_correct_module(module_name: str) -> Optional[str]:
    """
    Try to auto-correct an invalid module name using aliases.
    
    Args:
        module_name: Potentially incorrect module name
    
    Returns:
        Corrected module name or None if no correction found
    """
    # Already valid
    if is_valid_module(module_name):
        return module_name
    
    # Try case-insensitive match
    module_name_lower = module_name.lower()
    for valid_name in ALL_MODULES.keys():
        if valid_name.lower() == module_name_lower:
            return valid_name
    
    # Try aliases
    for valid_name, module_def in ALL_MODULES.items():
        if module_name.lower() in [alias.lower() for alias in module_def.aliases]:
            return valid_name
    
    return None


def get_compact_schema_section(language: str = "fr", top_k: int = 4) -> str:
    """
    Get a compact schema formatted for inclusion in LLM prompts.
    
    TICKET 3 (P0): Compact deterministic schema to reduce token usage and prevent
    random truncation. Shows only top-K most common actions per module.
    
    Args:
        language: "fr" or "en"
        top_k: Number of top actions to include per module (default: 4)
    
    Returns:
        Compact formatted schema string for LLM prompt
    """
    if language == "fr":
        prompt = """=== ACTIONS PRINCIPALES (Top-K par module) ===

"""
    else:
        prompt = """=== MAIN ACTIONS (Top-K per module) ===

"""
    
    # TICKET 3 (P0): Top-K action prioritization for compact schema
    # Define top-K actions per module (most commonly used, deterministic order)
    # These are the most frequently used actions based on typical workflows
    # MAINTENANCE: When adding/removing actions from module schemas, update this list
    # to ensure the most relevant actions are shown in the compact schema
    top_actions_per_module = {
        "system": ["open_application", "switch_application", "keystroke", "type"],
        "browser": ["open_url", "search", "navigate_back", "refresh"],
        "messaging": ["send_message", "open_thread", "search_messages", "read_channel_history"],
        "crm": ["open_record", "search_records", "update_field", "search_contact"],
        "files": ["open_file", "search_files", "read_file", "save_file"],
        "ui": ["click", "type", "copy", "paste"],
        "code": ["open_file", "find_text", "goto_line", "save_file"],
        "llm": ["summarize", "rewrite", "analyze_error", "answer_question"],
    }
    
    for module_name, module in ALL_MODULES.items():
        # Get top-K actions for this module
        top_action_names = top_actions_per_module.get(module_name, [])[:top_k]
        
        # Module name is language-agnostic
        prompt += f"{module_name}: "
        
        action_strs = []
        for action_name in top_action_names:
            action_def = module.get_action(action_name)
            if action_def:
                # Compact format: action_name(req_params)
                req_params = [p.name for p in action_def.parameters if p.required]
                if req_params:
                    param_str = ",".join(req_params)
                    action_strs.append(f"{action_name}({param_str})")
                else:
                    action_strs.append(f"{action_name}()")
            else:
                # DEFENSIVE: Log warning if action doesn't exist in module
                logger.warning(f"Action '{action_name}' not found in module '{module_name}' - update top_actions_per_module")
        
        prompt += ", ".join(action_strs) + "\n"
    
    if language == "fr":
        prompt += """
⚠️ Utilisez la syntaxe exacte: {"module":"nom","action":"nom","args":{...}}
"""
    else:
        prompt += """
⚠️ Use exact syntax: {"module":"name","action":"name","args":{...}}
"""
    
    return prompt


def get_prompt_schema_section(language: str = "fr") -> str:
    """
    Get the schema formatted for inclusion in LLM prompts.
    
    This is what should be injected into the ReasonerLLM prompt.
    
    Args:
        language: "fr" or "en"
    
    Returns:
        Formatted schema string for LLM prompt
    """
    if language == "fr":
        prompt = """=== MODULES DISPONIBLES (8 modules universels - STRICT) ===

Vous DEVEZ utiliser UNIQUEMENT les modules et actions listés ci-dessous.
TOUTE action non listée sera REJETÉE par le validateur.

"""
    else:
        prompt = """=== AVAILABLE MODULES (8 universal modules - STRICT) ===

You MUST use ONLY the modules and actions listed below.
ANY action not listed will be REJECTED by the validator.

"""
    
    for module_name, module in ALL_MODULES.items():
        if language == "fr":
            prompt += f"\n{module_name.upper()}. {module_name} : {module.description}\n"
        else:
            prompt += f"\n{module_name.upper()}. {module_name} : {module.description}\n"
        
        for action in module.actions:
            params = []
            for p in action.parameters:
                if p.required:
                    params.append(f"{p.name}*")
                else:
                    params.append(f"{p.name}")
            
            params_str = ", ".join(params) if params else "aucun paramètre" if language == "fr" else "no parameters"
            prompt += f"   - {action.name} : {action.description} ({params_str})\n"
    
    if language == "fr":
        prompt += """
⚠️ RÈGLES STRICTES :
1. N'utilisez QUE les actions listées ci-dessus
2. N'inventez JAMAIS de nouveaux noms d'actions
3. Respectez les paramètres requis (marqués *)
4. Si une action n'existe pas, utilisez la plus proche ou signalez l'erreur
"""
    else:
        prompt += """
⚠️ STRICT RULES:
1. Use ONLY the actions listed above
2. NEVER invent new action names
3. Respect required parameters (marked with *)
4. If an action doesn't exist, use the closest one or report error
"""
    
    return prompt
