import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import random
import sqlite3
import aiofiles

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configuración del bot con intenciones mejoradas
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# =============================================
# CONFIGURACIÓN DE BASE DE DATOS
# =============================================

async def setup_database():
    """Configurar la base de datos SQLite"""
    conn = sqlite3.connect('santiagoGuard.db')
    cursor = conn.cursor()
    
    # Crear tabla de advertencias si no existe
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS advertencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        admin_id TEXT NOT NULL,
        admin_name TEXT NOT NULL,
        reason TEXT NOT NULL,
        proof_url TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos configurada correctamente")

# =============================================
# CONSTANTES Y CONFIGURACIÓN
# =============================================
class Colors:
    PRIMARY = 0x5865F2  # Discord blurple
    SUCCESS = 0x57F287  # Discord green
    WARNING = 0xFEE75C  # Discord yellow
    DANGER = 0xED4245   # Discord red
    INFO = 0xEB459E     # Discord pink
    MUNICIPALITY = 0xF1C40F
    ILLEGAL = 0x992D22
    LEGAL = 0x1ABC9C
    APPEALS = 0xE67E22
    REPORTS = 0xE74C3C

class Channels:
    TICKETS = 1357151556926963751
    TICKET_LOGS = 1363220578638500001
    CONTROL_PANEL = 1357151558554620068
    ANNOUNCEMENTS = 1363046137996644453
    LOGS = 1363055208631898292
    STATUS = 1363060004017668246
    MEMBER_COUNT = 1363066378160050357

class Roles:
    STAFF = [1357151555916271624, 1357151555916271622, 1357151555916271618, 1357151555891232989, 1357151555891232984]
    ADMIN = 1357151555916271624
    MODERATOR = 1357151555916271622
    SUPPORT = 1357151555916271618

# Categorías de tickets con emojis únicos
TICKET_CATEGORIES = {
    "general_help": {
        "id": 1363245252990865468,
        "emoji": "🧩",
        "color": Colors.PRIMARY,
        "title": "Ayuda General",
        "description": "Para cualquier duda o problema general del servidor"
    },
    "municipality": {
        "id": 1363241205269528838,
        "emoji": "🏛️",
        "color": Colors.MUNICIPALITY,
        "title": "Municipalidad",
        "description": "Trámites municipales, licencias, propiedades"
    },
    "purchases": {
        "id": 1363245072509960464,
        "emoji": "🛍️",
        "color": Colors.SUCCESS,
        "title": "Compras",
        "description": "Problemas con compras, beneficios o paquetes VIP"
    },
    "benefits": {
        "id": 1363245136561045534,
        "emoji": "🎁",
        "color": Colors.INFO,
        "title": "Beneficios",
        "description": "Reclamos o consultas sobre beneficios especiales"
    },
    "alliances": {
        "id": 1363245200524312627,
        "emoji": "🤝",
        "color": Colors.PRIMARY,
        "title": "Alianzas",
        "description": "Solicitudes de alianzas entre facciones/empresas"
    },
    "doubts": {
        "id": 1363245252990865468,
        "emoji": "💭",
        "color": Colors.WARNING,
        "title": "Dudas",
        "description": "Consultas sobre reglas, mecánicas o funcionamiento"
    },
    "appeals": {
        "id": 1363245304106848557,
        "emoji": "📜",
        "color": Colors.APPEALS,
        "title": "Apelaciones",
        "description": "Apelar sanciones, baneos o advertencias"
    },
    "reports": {
        "id": 1363245369730797759,
        "emoji": "⚠️",
        "color": Colors.REPORTS,
        "title": "Reportes",
        "description": "Reportar jugadores, bugs o problemas graves"
    },
    "illegal_faction": {
        "id": 1363245470197088336,
        "emoji": "🕵️",
        "color": Colors.ILLEGAL,
        "title": "Facción Ilegal",
        "description": "Registro o consultas de facciones ilegales"
    },
    "robbery_claim": {
        "id": 1363245526396436611,
        "emoji": "🚔",
        "color": Colors.DANGER,
        "title": "Reclamo Robo",
        "description": "Reportar robos o pérdida de items/vehículos"
    },
    "business_creation": {
        "id": 1363245614816563351,
        "emoji": "🏢",
        "color": Colors.LEGAL,
        "title": "Creación Empresa",
        "description": "Solicitud para crear una empresa legal"
    },
    "ck_request": {
        "id": 1363245679983464750,
        "emoji": "💀",
        "color": Colors.DANGER,
        "title": "Solicitud CK",
        "description": "Solicitar Character Kill (muerte permanente)"
    }
}

# Estado del servidor
server_status = "indefinido"  # "abierto", "cerrado", "votacion", "indefinido"

# =============================================
# COMPONENTES UI PERSONALIZADOS
# =============================================
class VoteStartModal(ui.Modal, title="🗳️ Iniciar Votación"):
    votes_required = ui.TextInput(
        label="Número de votos requeridos",
        placeholder="Ej: 6",
        style=discord.TextStyle.short,
        required=True
    )
    
    authorized_by = ui.TextInput(
        label="Autorizado por (nombre sin @)",
        placeholder="Ej: Nicolas",
        style=discord.TextStyle.short,
        required=True
    )
    
    authorized_by_id = ui.TextInput(
        label="ID de Discord de quien autorizó",
        placeholder="Ej: 123456789012345678",
        style=discord.TextStyle.short,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class GradientButton(ui.Button):
    """Botón con efecto de gradiente personalizado"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.original_label = self.label
        self.original_style = self.style
        self.original_emoji = self.emoji
        
    async def callback(self, interaction: discord.Interaction):
        # Efecto visual al hacer clic
        self.style = discord.ButtonStyle.grey
        self.label = "⌛ Procesando..."
        self.emoji = None
        try:
            await interaction.message.edit(view=self.view)
        except:
            pass
        
        try:
            # Manejar diferentes botones según su custom_id
            if self.custom_id == "ticket_claim":
                await handle_ticket_claim(interaction)
            elif self.custom_id == "ticket_close":
                await handle_ticket_close(interaction)
            elif self.custom_id == "ticket_add_user":
                await handle_ticket_add_user(interaction)
            elif self.custom_id == "start_server":
                await handle_server_start(interaction)
            elif self.custom_id == "start_vote":
                await handle_vote_start(interaction)
            elif self.custom_id == "close_server":
                await handle_server_close(interaction)
            else:
                await super().callback(interaction)
        except Exception as e:
            print(f"Error en botón {self.custom_id}: {e}")
            try:
                await interaction.followup.send("❌ Ocurrió un error al procesar tu acción.", ephemeral=True)
            except:
                pass
        finally:
            # Restaurar estado original
            self.style = self.original_style
            self.label = self.original_label
            self.emoji = self.original_emoji
            try:
                await interaction.message.edit(view=self.view)
            except:
                pass

class AnimatedEmbed(discord.Embed):
    """Embed con efectos visuales dinámicos"""
    COLORS = [0x5865F2, 0xEB459E, 0x57F287, 0xFEE75C, 0xED4245]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = random.choice(self.COLORS)
        self._current_color = 0
        
    async def animate(self, channel):
        """Animar el embed cambiando colores"""
        message = await channel.send(embed=self)
        
        while True:
            self.color = self.COLORS[self._current_color % len(self.COLORS)]
            self._current_color += 1
            try:
                await message.edit(embed=self)
                await asyncio.sleep(10)
            except:
                break

# =============================================
# MODALES INTERACTIVOS
# =============================================
class CloseServerModal(ui.Modal, title="🔒 Cierre del Servidor"):
    reason = ui.TextInput(
        label="Razón del cierre",
        placeholder="Ej: Mantenimiento técnico, actualización...",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class GeneralHelpModal(ui.Modal, title="🧩 Solicitud de Ayuda"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    issue = ui.TextInput(
        label="Describe tu problema",
        style=discord.TextStyle.long,
        placeholder="Sé lo más detallado posible...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class MunicipalityModal(ui.Modal, title="🏛️ Trámite Municipal"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    procedure = ui.TextInput(
        label="¿Qué trámite necesitas?",
        style=discord.TextStyle.long,
        placeholder="Licencia, registro de vehículo, propiedad...",
        required=True
    )
    
    details = ui.TextInput(
        label="Detalles adicionales",
        style=discord.TextStyle.long,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class IllegalFactionModal(ui.Modal, title="🕵️ Creación de Facción Ilegal"):
    faction_name = ui.TextInput(
        label="Nombre de la Facción",
        placeholder="Ej: Cartel del Noroeste",
        required=True
    )
    
    owners = ui.TextInput(
        label="Dueño(s) (Roblox)",
        placeholder="Ej: Player1, Player2, Player3",
        style=discord.TextStyle.long,
        required=True
    )
    
    description = ui.TextInput(
        label="Descripción de la Facción",
        style=discord.TextStyle.long,
        placeholder="Describe los objetivos y actividades de tu facción",
        required=True
    )
    
    discord_link = ui.TextInput(
        label="Link de Discord de la facción",
        placeholder="https://discord.gg/...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class CloseTicketModal(ui.Modal, title="🔒 Cerrar Ticket"):
    reason = ui.TextInput(
        label="Razón del cierre",
        placeholder="Problema resuelto, usuario inactivo...",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class PurchasesModal(ui.Modal, title="🛍️ Ticket de Compras"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    issue = ui.TextInput(
        label="Razón del ticket",
        style=discord.TextStyle.long,
        placeholder="Describe tu problema con la compra...",
        required=True
    )
    
    payment_proof = ui.TextInput(
        label="Link del comprobante de pago (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ej: https://imgur.com/...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class BenefitsModal(ui.Modal, title="🎁 Reclamo de Beneficios"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    benefits = ui.TextInput(
        label="Beneficios a reclamar",
        style=discord.TextStyle.long,
        placeholder="Detalla qué beneficios quieres reclamar...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ej: https://imgur.com/...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class AlliancesModal(ui.Modal, title="🤝 Solicitud de Alianza"):
    server_name = ui.TextInput(
        label="Nombre del servidor",
        placeholder="Ej: Los Santos RP",
        style=discord.TextStyle.short,
        required=True
    )
    
    owner_name = ui.TextInput(
        label="Nombre de Discord del dueño",
        placeholder="Ej: Username#1234",
        style=discord.TextStyle.short,
        required=True
    )
    
    server_link = ui.TextInput(
        label="Link del servidor",
        placeholder="Ej: https://discord.gg/...",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class AppealsModal(ui.Modal, title="📜 Apelación"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    appeal_type = ui.TextInput(
        label="Tipo de apelación",
        placeholder="Sanción, Baneo o Advertencia",
        style=discord.TextStyle.short,
        required=True
    )
    
    appeal_reason = ui.TextInput(
        label="Razón de la apelación",
        style=discord.TextStyle.long,
        placeholder="Explica por qué deberías ser despenalizado...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ej: https://imgur.com/...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class ReportsModal(ui.Modal, title="⚠️ Reporte"):
    reported_name = ui.TextInput(
        label="Nombre de la persona a reportar",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    report_type = ui.TextInput(
        label="Tipo de reporte",
        placeholder="Usuario o Staff",
        style=discord.TextStyle.short,
        required=True
    )
    
    report_reason = ui.TextInput(
        label="Razón del reporte",
        style=discord.TextStyle.long,
        placeholder="Describe detalladamente el problema...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ej: https://imgur.com/...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class IllegalFactionModal(ui.Modal, title="🕵️ Facción Ilegal"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    faction_description = ui.TextInput(
        label="Descripción de la facción",
        style=discord.TextStyle.long,
        placeholder="Describe el propósito y actividades de la facción...",
        required=True
    )
    
    discord_link = ui.TextInput(
        label="Link de Discord de la facción",
        placeholder="Ej: https://discord.gg/...",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class RobberyClaimModal(ui.Modal, title="🚔 Reclamo de Robo"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    involved_players = ui.TextInput(
        label="Nombres de personas involucradas",
        style=discord.TextStyle.long,
        placeholder="Lista los nombres de Roblox de todos los involucrados...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ej: https://imgur.com/...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class BusinessCreationModal(ui.Modal, title="🏢 Creación de Empresa"):
    roblox_username = ui.TextInput(
        label="Nombre(s) de Roblox del/los dueño(s)",
        style=discord.TextStyle.long,
        placeholder="Ej: SantiagoRP_Player, OtroJugador...",
        required=True
    )
    
    business_description = ui.TextInput(
        label="Descripción de la empresa",
        style=discord.TextStyle.long,
        placeholder="Describe el propósito y servicios de la empresa...",
        required=True
    )
    
    business_type = ui.TextInput(
        label="Tipo de empresa",
        placeholder="Ej: Restaurante, Taller, Tienda...",
        style=discord.TextStyle.short,
        required=True
    )
    
    discord_link = ui.TextInput(
        label="Link de Discord de la empresa",
        placeholder="Ej: https://discord.gg/...",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class CKRequestModal(ui.Modal, title="💀 Solicitud de CK"):
    target_name = ui.TextInput(
        label="Nombre de la persona para CK",
        placeholder="Ej: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    ck_reason = ui.TextInput(
        label="Razón del CK",
        style=discord.TextStyle.long,
        placeholder="Explica detalladamente por qué solicitas el CK...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas",
        style=discord.TextStyle.short,
        placeholder="Ej: https://imgur.com/...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class AddUserModal(ui.Modal, title="➕ Agregar Usuario al Ticket"):
    username = ui.TextInput(
        label="Nombre de usuario de Discord",
        placeholder="Ej: Jrsmile22 (sin @)",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

# =============================================
# VISTAS INTERACTIVAS
# =============================================
class ControlPanelView(ui.View):
    """Panel de control con efectos visuales"""
    def __init__(self):
        super().__init__(timeout=None)
        
        # Botón para abrir servidor
        self.add_item(GradientButton(
            style=discord.ButtonStyle.success,
            label="Iniciar Servidor",
            emoji="🚀",
            custom_id="start_server"
        ))
        
        # Botón para votación
        self.add_item(GradientButton(
            style=discord.ButtonStyle.primary,
            label="Votación",
            emoji="🗳️",
            custom_id="start_vote"
        ))
        
        # Botón para cerrar servidor
        self.add_item(GradientButton(
            style=discord.ButtonStyle.danger,
            label="Cerrar Servidor",
            emoji="🔒",
            custom_id="close_server"
        ))

class TicketActionsView(ui.View):
    """Acciones para tickets con validación de roles"""
    def __init__(self):
        super().__init__(timeout=None)
        
        # Configurar botones con sus estilos y permisos
        self.add_item(GradientButton(
            style=discord.ButtonStyle.green,
            label="Reclamar",
            emoji="🛎️",
            custom_id="ticket_claim"
        ))
        
        self.add_item(GradientButton(
            style=discord.ButtonStyle.red,
            label="Cerrar",
            emoji="🔒",
            custom_id="ticket_close"
        ))
        
        self.add_item(GradientButton(
            style=discord.ButtonStyle.blurple,
            label="Agregar Usuario",
            emoji="➕",
            custom_id="ticket_add_user"
        ))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verificar que el usuario tenga permisos de staff"""
        if not any(role.id in Roles.STAFF for role in interaction.user.roles):
            error_embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="No tienes permisos para realizar esta acción.",
                color=Colors.DANGER
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return False
        return True

class TicketCreationView(ui.View):
    """Sistema de tickets interactivo"""
    def __init__(self):
        super().__init__(timeout=None)
        
        # Menú desplegable con categorías
        options = []
        for ticket_type, data in TICKET_CATEGORIES.items():
            options.append(discord.SelectOption(
                label=f"{data['emoji']} {data['title']}",
                value=ticket_type,
                description=data["description"][:100],
                emoji=data["emoji"]
            ))
        
        self.select = ui.Select(
            placeholder="🎫 Selecciona un tipo de ticket...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
    
    async def on_select(self, interaction: discord.Interaction):
            """Manejar selección de categoría"""
            category = self.select.values[0]
            
            # Mostrar formulario dinámico según categoría
            if category == "general_help":
                modal = GeneralHelpModal()
            elif category == "municipality":
                modal = MunicipalityModal()
            elif category == "illegal_faction":
                modal = IllegalFactionModal()
            elif category == "purchases":
                modal = PurchasesModal()
            elif category == "benefits":
                modal = BenefitsModal()
            elif category == "alliances":
                modal = AlliancesModal()
            elif category == "doubts":
                modal = GeneralHelpModal(title="💭 Dudas")
            elif category == "appeals":
                modal = AppealsModal()
            elif category == "reports":
                modal = ReportsModal()
            elif category == "robbery_claim":
                modal = RobberyClaimModal()
            elif category == "business_creation":
                modal = BusinessCreationModal()
            elif category == "ck_request":
                modal = CKRequestModal()
            else:
                modal = GeneralHelpModal(title=f"{TICKET_CATEGORIES[category]['emoji']} {TICKET_CATEGORIES[category]['title']}")
            
            await interaction.response.send_modal(modal)
            
            try:
                # Fix: Use timeout in wait_for instead of as a parameter to wait()
                timed_out = await modal.wait()
                if timed_out:
                    return await interaction.followup.send("⌛ Tiempo agotado. Por favor intenta nuevamente.", ephemeral=True)
                
                # Procesar datos del formulario
                data = {}
                for child in modal.children:
                    if isinstance(child, ui.TextInput):
                        data[child.label] = child.value
                
                await create_ticket_channel(
                    interaction=modal.interaction,
                    category=category,
                    data=data
                )
            except Exception as e:
                print(f"Error al procesar ticket: {e}")
                await interaction.followup.send("❌ Ocurrió un error al crear tu ticket.", ephemeral=True)

# =============================================
# FUNCIONES PRINCIPALES
# =============================================
async def update_status_channel():
    """Actualizar el canal de estado"""
    channel = bot.get_channel(Channels.STATUS)
    if not channel:
        return
    
    status_map = {
        "abierto": "🟢│servidor-encendido",
        "cerrado": "🔴│server-cerrado",
        "votacion": "🟡│votación-activa",
        "indefinido": "⚪│estado-indefinido"
    }
    
    new_name = status_map.get(server_status, "⚪│estado-indefinido")
    
    if channel.name != new_name:
        try:
            await channel.edit(name=new_name)
            print(f"✅ Canal de estado actualizado a: {new_name}")
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limit error code
                retry_after = e.retry_after or 60
                print(f"⚠️ Rate limit alcanzado al actualizar canal de estado. Esperando {retry_after:.2f} segundos.")
                # No intentar nuevamente para evitar más rate limits
            else:
                print(f"Error al actualizar canal de estado: {e}")

async def update_member_count():
    """Actualizar el canal de conteo de miembros"""
    channel = bot.get_channel(Channels.MEMBER_COUNT)
    if not channel:
        return
    
    real_members = sum(1 for member in channel.guild.members if not member.bot)
    emojis = ["🌎", "👥", "🚀", "💫", "🌟"]
    emoji = emojis[real_members % len(emojis)]
    new_name = f"{emoji}│miembros-{real_members}"
    
    if channel.name != new_name:
        try:
            await channel.edit(name=new_name)
            print(f"✅ Canal de miembros actualizado a: {new_name}")
        except discord.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ Rate limit alcanzado al actualizar canal de miembros. Esperando {e.retry_after:.2f} segundos.")
                # No intentar nuevamente para evitar más rate limits
            else:
                print(f"Error al actualizar conteo de miembros: {e}")

async def create_ticket_channel(interaction: discord.Interaction, category: str, data: dict):
    """Crear un canal de ticket profesional"""
    try:
        category_info = TICKET_CATEGORIES.get(category, {})
        
        # Configurar permisos
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Agregar permisos para staff
        for role_id in Roles.STAFF:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
        
        # Crear el canal
        ticket_num = len([c for c in interaction.guild.get_channel(category_info["id"]).channels 
                         if c.name.startswith(f"{category}-")]) + 1
        channel_name = f"{category}-{ticket_num}-{interaction.user.name}"[:100]
        
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=discord.Object(id=category_info["id"]),
            overwrites=overwrites
        )
        
        # Crear embed del ticket
        embed = AnimatedEmbed(
            title=f"{category_info['emoji']} Ticket de {category_info['title']}",
            description=f"**Usuario:** {interaction.user.mention}\n"
                      f"**Tipo:** {category_info['title']}",
            color=category_info["color"]
        )
        
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        for field, value in data.items():
            embed.add_field(name=field, value=value or "No especificado", inline=False)
        
        embed.set_footer(text=f"Ticket creado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}")
        
        # Enviar embed con acciones
        view = TicketActionsView()
        message = await ticket_channel.send(
            content=f"🎟️ {interaction.user.mention} | Staff: Por favor atiendan este ticket",
            embed=embed,
            view=view
        )
        await message.pin()
        
        # Confirmación al usuario
        confirm_embed = discord.Embed(
            title="✅ Ticket Creado Exitosamente",
            description=f"Se ha creado tu ticket en {ticket_channel.mention}",
            color=Colors.SUCCESS
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        
        # Enviar a logs
        log_channel = bot.get_channel(Channels.TICKET_LOGS)
        if log_channel:
            log_embed = discord.Embed(
                title=f"{category_info['emoji']} Nuevo Ticket Creado",
                description=f"**Tipo:** {category_info['title']}\n"
                          f"**Usuario:** {interaction.user.mention}\n"
                          f"**Canal:** {ticket_channel.mention}",
                color=category_info["color"],
                timestamp=datetime.now()
            )
            await log_channel.send(embed=log_embed)
        
    except Exception as e:
        print(f"Error al crear ticket: {e}")
        error_embed = discord.Embed(
            title="❌ Error al Crear Ticket",
            description="Ocurrió un error al crear tu ticket. Por favor inténtalo nuevamente.",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

async def send_announcement(interaction: discord.Interaction, embed: discord.Embed, action: str):
    """Enviar anuncio al canal correspondiente"""
    channel = bot.get_channel(Channels.ANNOUNCEMENTS)
    
    try:
        await channel.purge(limit=5)
        message = await channel.send(embed=embed)
        
        log_embed = discord.Embed(
            title=f"📢 {action.upper()}",
            description=f"Acción realizada por {interaction.user.mention}",
            color=embed.color
        )
        
        log_channel = bot.get_channel(Channels.LOGS)
        await log_channel.send(embed=log_embed)
        
        return message
    except Exception as e:
        print(f"Error al enviar anuncio: {e}")
        await interaction.followup.send(
            "❌ No se pudo enviar el anuncio",
            ephemeral=True
        )

# =============================================
# MANEJADORES DE INTERACCIONES PARA TICKETS
# =============================================
async def handle_ticket_claim(interaction: discord.Interaction):
    """Manejar reclamación de ticket"""
    # Verificar si el usuario tiene rol de staff
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ Solo el staff puede reclamar tickets.",
            ephemeral=True
        )
    
    # Obtener el embed original y añadir campo de atención
    embed = interaction.message.embeds[0]
    
    # Verificar si ya está reclamado
    for field in embed.fields:
        if field.name == "🛎️ Atendido por":
            return await interaction.response.send_message(
                "❌ Este ticket ya ha sido reclamado.",
                ephemeral=True
            )
    
    # Añadir campo de atención
    embed.add_field(
        name="🛎️ Atendido por",
        value=interaction.user.mention,
        inline=False
    )
    
    # Crear una nueva vista con el botón de reclamar deshabilitado
    new_view = TicketActionsView()
    for child in new_view.children:
        if child.custom_id == "ticket_claim":
            child.disabled = True
            child.label = "Reclamado"
            child.style = discord.ButtonStyle.grey
    
    # Enviar confirmación al usuario primero
    await interaction.response.send_message(
        "✅ Has reclamado este ticket!",
        ephemeral=True
    )
    
    # Luego actualizar mensaje original
    await interaction.message.edit(embed=embed, view=new_view)
    
    # Enviar mensaje embebido de atención
    attention_embed = discord.Embed(
        title="🛎️ Ticket Reclamado",
        description=f"### ¡Buenas noticias!\n\n"
                  f"Tu ticket será atendido por {interaction.user.mention}.\n\n"
                  f"Por favor, ten paciencia mientras revisa tu caso y te brinda la asistencia necesaria.",
        color=Colors.SUCCESS,
        timestamp=datetime.now()
    )
    attention_embed.set_thumbnail(url=interaction.user.display_avatar.url)
    attention_embed.set_footer(text=f"Staff: {interaction.user.display_name}")
    
    await interaction.channel.send(embed=attention_embed)

async def handle_ticket_close(interaction: discord.Interaction):
    """Manejar cierre de ticket con confirmación"""
    # Mostrar modal para razón de cierre
    modal = CloseTicketModal()
    await interaction.response.send_modal(modal)
    
    # Esperar a que se complete el modal
    timed_out = await modal.wait()
    if timed_out:
        return
    
    # Enviar mensaje de cierre inminente
    closing_embed = discord.Embed(
        title="🔒 Cerrando Ticket...",
        description=f"Este ticket se cerrará en 5 segundos.\n**Razón:** {modal.reason.value}",
        color=Colors.DANGER
    )
    await modal.interaction.followup.send(embed=closing_embed)
    
    # Enviar a logs
    log_channel = bot.get_channel(Channels.TICKET_LOGS)
    if log_channel:
        log_embed = discord.Embed(
            title="📌 Ticket Cerrado",
            description=f"**Canal:** {interaction.channel.name}\n"
                      f"**Cerrado por:** {interaction.user.mention}\n"
                      f"**Razón:** {modal.reason.value}",
            color=Colors.DANGER,
            timestamp=datetime.now()
        )
        await log_channel.send(embed=log_embed)
    
    # Esperar 5 segundos y cerrar
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete(
            reason=f"Cerrado por {interaction.user}. Razón: {modal.reason.value}"
        )
    except Exception as e:
        print(f"Error al eliminar canal: {e}")
        await modal.interaction.followup.send(
            "❌ No se pudo eliminar el canal. Por favor, ciérralo manualmente.",
            ephemeral=True
        )

async def handle_ticket_add_user(interaction: discord.Interaction):
    """Manejar agregar usuario a ticket"""
    # Mostrar modal para ingresar nombre de usuario
    modal = AddUserModal()
    await interaction.response.send_modal(modal)
    
    # Esperar a que se complete el modal
    timed_out = await modal.wait()
    if timed_out:
        return
    
    # Buscar al usuario mencionado
    username = modal.username.value
    member = None
    
    # Buscar por nombre de usuario sin discriminator
    for guild_member in interaction.guild.members:
        if guild_member.name.lower() == username.lower():
            member = guild_member
            break
    
    if not member:
        error_embed = discord.Embed(
            title="❌ Usuario no encontrado",
            description=f"No se encontró al usuario '{username}' en el servidor.",
            color=Colors.DANGER
        )
        return await modal.interaction.followup.send(embed=error_embed, ephemeral=True)
    
    # Agregar permisos al usuario
    await interaction.channel.set_permissions(
        member,
        read_messages=True,
        send_messages=True,
        view_channel=True
    )
    
    # Confirmar la acción
    confirm_embed = discord.Embed(
        title="✅ Usuario Agregado",
        description=f"Se ha agregado a {member.mention} al ticket.",
        color=Colors.SUCCESS
    )
    await modal.interaction.followup.send(embed=confirm_embed, ephemeral=True)
    
    # Notificar en el canal del ticket
    ticket_embed = discord.Embed(
        title="➕ Usuario Agregado",
        description=f"{member.mention} ha sido agregado al ticket por {interaction.user.mention}.",
        color=Colors.SUCCESS
    )
    await interaction.channel.send(embed=ticket_embed)

# =============================================
# MANEJADORES DE INTERACCIONES PARA PANEL DE CONTROL
# =============================================
async def handle_server_start(interaction: discord.Interaction):
    """Manejar inicio del servidor"""
    global server_status
    
    # Verificar si el usuario tiene permisos
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ No tienes permisos para iniciar el servidor.",
            ephemeral=True
        )
    
    # Cambiar estado del servidor
    server_status = "abierto"
    
    # Crear anuncio mejorado
    embed = discord.Embed(
        title="🚀 ¡SERVIDOR SANTIAGO RP ABIERTO!",
        description="### ¡El servidor de Santiago RP está ahora abierto!\n\n"
                  "Todos los jugadores pueden conectarse y disfrutar de la experiencia.\n\n"
                  "### 📱 Métodos para unirte:\n\n"
                  "**1️⃣ Desde la lista de servidores:**\n"
                  "> En ajustes del juego ERLC, apartado de servidores\n"
                  "> Busca: **S SANTIAGO RP | ESTRICTO | SPANISH**\n\n"
                  "**2️⃣ Con código de servidor:**\n"
                  "> En ajustes del juego ERLC, apartado de servidor con código\n"
                  "> Ingresa el código: **STRPP**\n\n"
                  "**3️⃣ Desde PC/Laptop:**\n"
                  "> Usa este enlace directo:\n"
                  "> [Unirse ahora](https://policeroleplay.community/join?code=STRPP)",
        color=Colors.SUCCESS,
        timestamp=datetime.now()
    )
    
    # Añadir imagen grande
    embed.set_image(url="https://media.discordapp.net/attachments/1340184960379781191/1363350692651335903/RobloxScreenShot20250416_193740099_1.jpg")
    
    # Añadir miniatura (foto de perfil del servidor)
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    
    embed.add_field(
        name="Abierto por",
        value=interaction.user.mention,
        inline=True
    )
    
    embed.add_field(
        name="Estado",
        value="🟢 Abierto",
        inline=True
    )
    
    embed.set_footer(text="Santiago RP - Servidor Oficial")
    
    # Enviar anuncio
    await send_announcement(interaction, embed, "Servidor Abierto")
    
    # Confirmar al usuario
    await interaction.response.send_message(
        "✅ Has abierto el servidor correctamente!",
        ephemeral=True
    )

async def handle_vote_start(interaction: discord.Interaction):
    """Manejar inicio de votación para abrir el servidor"""
    global server_status
    
    # Verificar si el usuario tiene permisos
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ No tienes permisos para iniciar una votación.",
            ephemeral=True
        )
    
    # Mostrar modal para obtener información adicional
    modal = VoteStartModal()
    await interaction.response.send_modal(modal)
    
    # Esperar a que se complete el modal
    timed_out = await modal.wait()
    if timed_out:
        return
    
    # Cambiar estado del servidor
    server_status = "votacion"
    
    # Buscar al usuario que autorizó por nombre
    authorized_user = None
    authorized_mention = f"@{modal.authorized_by.value}"
    
    # Si se proporcionó un ID, intentar encontrar al usuario por ID
    if modal.authorized_by_id.value:
        try:
            authorized_user = await interaction.guild.fetch_member(int(modal.authorized_by_id.value))
            if authorized_user:
                authorized_mention = authorized_user.mention
        except:
            pass
    
    # Si no se encontró por ID, buscar por nombre
    if not authorized_user:
        for member in interaction.guild.members:
            if member.name.lower() == modal.authorized_by.value.lower():
                authorized_user = member
                authorized_mention = member.mention
                break
    
    # Crear anuncio mejorado
    embed = discord.Embed(
        title="🗳️ ¡ENCUESTA INICIADA!",
        description="### Hemos habilitado una encuesta para que puedan votar sobre la fecha de apertura del servidor.\n\n"
                  "**Reglas del servidor:**\n\n"
                  "• Al votar, comprométase a participar activamente en el rol.\n"
                  "• Abstenerse de realizar antirol.\n"
                  "• Es imprescindible leer y cumplir con las normativas del servidor.\n"
                  "• No se permite estar en facciones sin el rol correspondiente.\n"
                  "• Evite forzar el rol de otros.\n\n"
                  "El incumplimiento del rol establecido será sancionado.\n\n"
                  f"**Equipo de moderación:** Activo y disponible para asistir en cualquier incidencia.\n\n"
                  f"**Se requiere un mínimo de {modal.votes_required.value} votos para proceder con la apertura.**\n\n"
                  f"**Reacciona con 👍 para votar a favor o 👎 para votar en contra.**",
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    
    # Añadir imagen grande
    embed.set_image(url="https://media.discordapp.net/attachments/1360714101327663135/1360762037495529672/Screenshot_20250412_194212_CapCut.jpg")
    
    # Añadir miniatura (foto de perfil del usuario)
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    
    embed.add_field(
        name="Estado",
        value="🟡 En votación",
        inline=True
    )
    
    embed.add_field(
        name="Autorizado Por",
        value=authorized_mention,
        inline=True
    )
    
    embed.add_field(
        name="Moderador Responsable",
        value=interaction.user.mention,
        inline=True
    )
    
    embed.set_footer(text="Santiago RP - Servidor Oficial")
    
    # Enviar anuncio
    message = await send_announcement(interaction, embed, "Votación Iniciada")
    
    # Añadir reacciones para votar
    if message:
        await message.add_reaction("👍")  # Voto a favor
        await message.add_reaction("👎")  # Voto en contra
    
    # Confirmar al usuario
    await modal.interaction.followup.send(
        "✅ Has iniciado una votación correctamente!",
        ephemeral=True
    )

async def handle_server_close(interaction: discord.Interaction):
    """Manejar cierre del servidor"""
    global server_status
    
    # Verificar si el usuario tiene permisos
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ No tienes permisos para cerrar el servidor.",
            ephemeral=True
        )
    
    # Mostrar modal para razón de cierre
    modal = CloseServerModal()
    await interaction.response.send_modal(modal)
    
    # Esperar a que se complete el modal
    timed_out = await modal.wait()
    if timed_out:
        return
    
    # Cambiar estado del servidor
    server_status = "cerrado"
    await update_status_channel()
    
    # Crear anuncio
    embed = discord.Embed(
        title="🔒 SERVIDOR CERRADO",
        description=f"### El servidor de Santiago RP está temporalmente cerrado\n\n"
                  f"**Razón:** {modal.reason.value}",
        color=Colors.DANGER,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Cerrado por",
        value=interaction.user.mention,
        inline=True
    )
    
    embed.add_field(
        name="Estado",
        value="🔴 Cerrado",
        inline=True
    )
    
    embed.set_footer(text="Santiago RP - Servidor Oficial")
    
    # Enviar anuncio
    await send_announcement(interaction, embed, "Servidor Cerrado")
    
    # Confirmar al usuario
    await modal.interaction.followup.send(
        "✅ Has cerrado el servidor correctamente!",
        ephemeral=True
    )

# =============================================
# COMANDOS Y EVENTOS
# =============================================
# In the on_ready event, let's modify how we handle initial updates
@bot.event
async def on_ready():
    print(f'✨ {bot.user.name} está listo!')
    
    # Iniciar la rotación de actividades
    bot.loop.create_task(rotate_activities())
    
    try:
        await bot.tree.sync()
        print("🔁 Comandos sincronizados")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")
    
    # Actualizar canales de estado con retraso para evitar rate limits
    bot.loop.create_task(delayed_initial_update())

async def rotate_activities():
    """Rotar entre diferentes actividades del bot"""
    while True:
        # Obtener el total de miembros reales (no bots)
        guild = bot.get_guild(next(iter(bot.guilds)).id)  # Obtener el primer servidor
        real_members = sum(1 for member in guild.members if not member.bot)
        
        activities = [
            discord.Activity(
                type=discord.ActivityType.watching,
                name=f"Santiago RP | {real_members} miembros"
            ),
            discord.Activity(
                type=discord.ActivityType.playing,
                name="Creado por Smile"
            ),
            discord.Activity(
                type=discord.ActivityType.listening,
                name="SantiagoRP | El mejor RP"
            )
        ]
        
        for activity in activities:
            await bot.change_presence(activity=activity)
            await asyncio.sleep(60)  # Cambiar cada 60 segundos
    
async def delayed_initial_update():
    """Realizar actualizaciones iniciales con retrasos para evitar rate limits"""
    # Primero actualizar el conteo de miembros
    await update_member_count()
    
    # Esperar 60 segundos antes de actualizar el canal de estado
    await asyncio.sleep(60)
    await update_status_channel()
    
    # Iniciar la tarea periódica después
    bot.loop.create_task(periodic_status_update())

async def periodic_status_update():
    """Actualizar el estado del canal periódicamente para evitar rate limits"""
    while True:
        try:
            await update_status_channel()
        except Exception as e:
            print(f"Error en actualización periódica: {e}")
        # Esperar 15 minutos entre actualizaciones
        await asyncio.sleep(900)  # Aumentado a 15 minutos

@bot.tree.command(name="panel", description="Despliega el panel de control administrativo")
@app_commands.checks.has_any_role(*Roles.STAFF)  
async def control_panel(interaction: discord.Interaction):
    """Comando para mostrar el panel de control"""
    embed = AnimatedEmbed(
        title="⚙️ PANEL DE CONTROL SANTIAGO RP",
        description="Gestiona el servidor con los controles a continuación:"
    )
    
    embed.add_field(
        name="🚀 Iniciar Servidor",
        value="Abre el servidor para todos los jugadores",
        inline=True
    )
    
    embed.add_field(
        name="🗳️ Iniciar Votación",
        value="Permite al staff votar para abrir el servidor",
        inline=True
    )
    
    embed.add_field(
        name="🔒 Cerrar Servidor",
        value="Cierra el servidor temporalmente",
        inline=True
    )
    
    embed.set_footer(text="Solo para uso administrativo")
    
    await interaction.response.send_message(
        embed=embed,
        view=ControlPanelView()
    )

@bot.tree.command(name="tickets", description="Configura el sistema de tickets")
@app_commands.checks.has_any_role(*Roles.STAFF)
async def setup_tickets(interaction: discord.Interaction):
    """Comando para configurar el sistema de tickets"""
    embed = AnimatedEmbed(
        title="🎫 SISTEMA DE TICKETS",
        description="Selecciona el tipo de ticket que necesitas:"
    )
    
    # Agrupar tickets por categorías
    embed.add_field(
        name="🧩 Asistencia General",
        value="\n".join([
            f"{data['emoji']} **{data['title']}** - {data['description']}"
            for cat, data in TICKET_CATEGORIES.items() 
            if cat in ["general_help", "doubts"]
        ]),
        inline=False
    )
    
    embed.add_field(
        name="🏛️ Trámites Oficiales",
        value="\n".join([
            f"{data['emoji']} **{data['title']}** - {data['description']}"
            for cat, data in TICKET_CATEGORIES.items() 
            if cat in ["municipality", "business_creation", "illegal_faction"]
        ]),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Reportes y Problemas",
        value="\n".join([
            f"{data['emoji']} **{data['title']}** - {data['description']}"
            for cat, data in TICKET_CATEGORIES.items() 
            if cat in ["purchases", "benefits", "reports", "robbery_claim", "appeals"]
        ]),
        inline=False
    )
    
    embed.set_footer(text="Selecciona una opción del menú para comenzar")
    
    await interaction.response.send_message(
        embed=embed,
        view=TicketCreationView()
    )

# Función de autocompletado para usuarios
async def usuario_autocompletar(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocompletar usuarios del servidor basado en lo que el usuario está escribiendo"""
    members = interaction.guild.members
    choices = []
    
    # Si no hay texto de búsqueda, mostrar algunos miembros recientes o destacados
    if not current:
        # Obtener algunos miembros para mostrar por defecto (limitado a 25)
        for member in list(members)[:25]:
            if not member.bot:  # Excluir bots
                display_text = f"{member.display_name}"
                if member.name != member.display_name:
                    display_text = f"{member.display_name} (@{member.name})"
                
                choices.append(app_commands.Choice(
                    name=display_text,
                    value=str(member.id)
                ))
        return choices
    
    # Filtrar miembros que coincidan con lo que el usuario está escribiendo
    current = current.lower()
    for member in members:
        if not member.bot and (current in member.name.lower() or current in member.display_name.lower()):
            # Crear un nombre de visualización más descriptivo
            display_text = f"{member.display_name}"
            if member.name != member.display_name:
                display_text = f"{member.display_name} (@{member.name})"
            
            # Añadir al usuario a las opciones
            choices.append(app_commands.Choice(
                name=display_text,
                value=str(member.id)
            ))
            # Limitar a 25 opciones (límite de Discord)
            if len(choices) >= 25:
                break
    
    return choices

@bot.tree.command(name="advertencia-a", description="Emite una advertencia oficial a un usuario")
@app_commands.describe(
    usuario="El usuario que recibirá la advertencia",
    razon="Motivo de la advertencia",
    prueba="URL de la imagen que sirve como prueba (opcional)"
)
@app_commands.autocomplete(usuario=usuario_autocompletar)
@app_commands.checks.has_any_role(*Roles.STAFF)
async def advertencia(interaction: discord.Interaction, usuario: str, razon: str, prueba: str = None):
    """Comando para emitir advertencias oficiales"""
    
    # Verificar si el usuario tiene permisos
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ No tienes permisos para emitir advertencias.",
            ephemeral=True
        )
    
    # Obtener el miembro a partir del ID
    try:
        usuario_obj = await interaction.guild.fetch_member(int(usuario))
    except (discord.NotFound, ValueError):
        return await interaction.response.send_message(
            "❌ No se pudo encontrar al usuario especificado.",
            ephemeral=True
        )
    
    # Crear embed para la advertencia
    embed = discord.Embed(
        title="⚠️ ADVERTENCIA OFICIAL",
        description=f"Se ha emitido una advertencia oficial contra {usuario_obj.mention}",
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📝 Razón",
        value=razon,
        inline=False
    )
    
    embed.add_field(
        name="👮‍♂️ Administrador",
        value=interaction.user.mention,
        inline=True
    )
    
    embed.add_field(
        name="📅 Fecha",
        value=datetime.now().strftime("%d/%m/%Y %H:%M"),
        inline=True
    )
    
    # Añadir imagen de prueba si se proporciona
    if prueba:
        embed.add_field(
            name="🔍 Prueba",
            value=f"[Ver imagen]({prueba})",
            inline=False
        )
        embed.set_image(url=prueba)
    
    embed.set_thumbnail(url=usuario.display_avatar.url)
    embed.set_footer(text=f"Santiago RP - Sistema de Advertencias • ID: {usuario.id}")
    
    # Responder al comando
    await interaction.response.send_message(
        f"✅ Advertencia emitida a {usuario.mention} correctamente.",
        embed=embed
    )
    
    # Enviar mensaje directo al usuario
    try:
        dm_embed = discord.Embed(
            title="⚠️ HAS RECIBIDO UNA ADVERTENCIA",
            description=f"Has recibido una advertencia oficial en **{interaction.guild.name}**",
            color=Colors.DANGER,
            timestamp=datetime.now()
        )
        
        dm_embed.add_field(
            name="📝 Razón",
            value=razon,
            inline=False
        )
        
        dm_embed.add_field(
            name="👮‍♂️ Administrador",
            value=f"{interaction.user.name}",
            inline=True
        )
        
        dm_embed.add_field(
            name="📅 Fecha",
            value=datetime.now().strftime("%d/%m/%Y %H:%M"),
            inline=True
        )
        
        dm_embed.add_field(
            name="⚠️ Importante",
            value="Si crees que esta advertencia es injusta, puedes apelar abriendo un ticket en el servidor.",
            inline=False
        )
        
        if prueba:
            dm_embed.add_field(
                name="🔍 Prueba",
                value=f"[Ver imagen]({prueba})",
                inline=False
            )
            dm_embed.set_image(url=prueba)
        
        dm_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
        dm_embed.set_footer(text=f"Santiago RP - Sistema de Advertencias • ID: {usuario.id}")
        
        await usuario.send(embed=dm_embed)
        
    except Exception as e:
        print(f"Error al enviar DM: {e}")
        await interaction.followup.send(
            f"⚠️ No se pudo enviar un mensaje directo a {usuario.mention}. La advertencia ha sido registrada de todos modos.",
            ephemeral=True
        )
    
    # Enviar a canal de logs
    log_channel = bot.get_channel(Channels.LOGS)
    if log_channel:
        await log_channel.send(embed=embed)
    
    # Guardar en la base de datos
    try:
        conn = sqlite3.connect('santiagoGuard.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO advertencias (user_id, user_name, admin_id, admin_name, reason, proof_url)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            str(usuario.id),
            usuario.name,
            str(interaction.user.id),
            interaction.user.name,
            razon,
            prueba
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error al guardar en la base de datos: {e}")
        await interaction.followup.send(
            "⚠️ Ocurrió un error al guardar la advertencia en la base de datos.",
            ephemeral=True
        )

@bot.tree.command(name="historial-advertencias", description="Muestra el historial de advertencias de un usuario")
@app_commands.describe(
    usuario="El usuario del que quieres ver las advertencias"
)
@app_commands.autocomplete(usuario=usuario_autocompletar)
@app_commands.checks.has_any_role(*Roles.STAFF)
async def historial_advertencias(interaction: discord.Interaction, usuario: str):
    """Comando para ver el historial de advertencias de un usuario"""
    
    # Verificar si el usuario tiene permisos
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ No tienes permisos para ver el historial de advertencias.",
            ephemeral=True
        )
    
    # Obtener el miembro a partir del ID
    try:
        usuario_obj = await interaction.guild.fetch_member(int(usuario))
    except (discord.NotFound, ValueError):
        return await interaction.response.send_message(
            "❌ No se pudo encontrar al usuario especificado.",
            ephemeral=True
        )
    
    try:
        conn = sqlite3.connect('santiagoGuard.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, admin_name, reason, proof_url, timestamp
        FROM advertencias
        WHERE user_id = ?
        ORDER BY timestamp DESC
        ''', (str(usuario.id),))
        
        advertencias = cursor.fetchall()
        conn.close()
        
        if not advertencias:
            return await interaction.response.send_message(
                f"✅ {usuario.mention} no tiene advertencias registradas.",
                ephemeral=True
            )
        
        embed = discord.Embed(
            title=f"📋 Historial de Advertencias",
            description=f"Usuario: {usuario.mention}\nTotal: {len(advertencias)} advertencia(s)",
            color=Colors.WARNING,
            timestamp=datetime.now()
        )
        
        for i, (adv_id, admin, razon, prueba, fecha) in enumerate(advertencias, 1):
            fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            
            value = f"**Razón:** {razon}\n**Admin:** {admin}\n**Fecha:** {fecha_formateada}"
            if prueba:
                value += f"\n**Prueba:** [Ver imagen]({prueba})"
                
            embed.add_field(
                name=f"⚠️ Advertencia #{adv_id}",
                value=value,
                inline=False
            )
        
        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.set_footer(text=f"Santiago RP - Sistema de Advertencias • ID: {usuario.id}")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"Error al obtener historial: {e}")
        await interaction.response.send_message(
            "❌ Ocurrió un error al obtener el historial de advertencias.",
            ephemeral=True
        )

# =============================================
# EVENTOS ADICIONALES
# =============================================
@bot.event
async def on_member_join(member: discord.Member):
    """Actualizar conteo de miembros cuando alguien se une"""
    await update_member_count()

@bot.event
async def on_member_remove(member: discord.Member):
    """Actualizar conteo de miembros cuando alguien se va"""
    await update_member_count()

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error):
    """Manejar errores de comandos de aplicación"""
    if isinstance(error, app_commands.errors.MissingAnyRole):
        await interaction.response.send_message(
            "❌ No tienes los permisos necesarios para usar este comando.",
            ephemeral=True
        )
    else:
        print(f"Error en comando: {error}")
        await interaction.response.send_message(
            "❌ Ocurrió un error al ejecutar el comando.",
            ephemeral=True
        )

# =============================================
# INICIAR BOT
# =============================================
if __name__ == "__main__":
    bot.run(TOKEN)