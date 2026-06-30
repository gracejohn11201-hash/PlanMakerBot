import os
import json
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# User data storage (in-memory)
user_plans = {}
user_sessions = {}

# ==================== PLAN FUNCTIONS ====================
def create_plan(user_id, title, tasks, priority="medium", due_date=None):
    """Create a new plan"""
    if user_id not in user_plans:
        user_plans[user_id] = []
    
    plan = {
        "id": len(user_plans[user_id]) + 1,
        "title": title,
        "tasks": tasks,
        "priority": priority,
        "due_date": due_date,
        "created_at": datetime.now().isoformat(),
        "completed": False
    }
    user_plans[user_id].append(plan)
    return plan

def get_plans(user_id, filter_type="all"):
    """Get plans for a user with optional filter"""
    if user_id not in user_plans:
        return []
    
    plans = user_plans[user_id]
    
    if filter_type == "active":
        return [p for p in plans if not p["completed"]]
    elif filter_type == "completed":
        return [p for p in plans if p["completed"]]
    elif filter_type == "high":
        return [p for p in plans if p["priority"] == "high"]
    elif filter_type == "medium":
        return [p for p in plans if p["priority"] == "medium"]
    elif filter_type == "low":
        return [p for p in plans if p["priority"] == "low"]
    else:
        return plans

def toggle_plan_completion(user_id, plan_id):
    """Toggle plan completion status"""
    if user_id not in user_plans:
        return False
    
    for plan in user_plans[user_id]:
        if plan["id"] == plan_id:
            plan["completed"] = not plan["completed"]
            return True
    return False

def delete_plan(user_id, plan_id):
    """Delete a plan"""
    if user_id not in user_plans:
        return False
    
    user_plans[user_id] = [p for p in user_plans[user_id] if p["id"] != plan_id]
    return True

def format_plans_list(plans, title="📋 Your Plans"):
    """Format plans for display"""
    if not plans:
        return "📋 **No plans found**\n\nCreate your first plan with /newplan!"
    
    result = f"📋 **{title}**\n\n"
    
    for plan in plans:
        status = "✅" if plan["completed"] else "⏳"
        priority_emoji = "🔴" if plan["priority"] == "high" else "🟡" if plan["priority"] == "medium" else "🟢"
        
        result += f"{status} **#{plan['id']}** {plan['title']}\n"
        result += f"   {priority_emoji} {plan['priority'].title()}"
        
        if plan.get("due_date"):
            result += f" | 📅 {plan['due_date']}"
        
        result += f"\n   📝 Tasks: {len(plan['tasks'])}\n\n"
    
    return result

# ==================== KEYBOARD FUNCTIONS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 My Plans", callback_data="plans")],
        [InlineKeyboardButton("➕ New Plan", callback_data="new")],
        [InlineKeyboardButton("📊 Filter Plans", callback_data="filter")],
        [InlineKeyboardButton("📝 Today's Tasks", callback_data="today")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_filter_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 All", callback_data="filter_all")],
        [InlineKeyboardButton("⏳ Active", callback_data="filter_active")],
        [InlineKeyboardButton("✅ Completed", callback_data="filter_completed")],
        [InlineKeyboardButton("🔴 High Priority", callback_data="filter_high")],
        [InlineKeyboardButton("🟡 Medium Priority", callback_data="filter_medium")],
        [InlineKeyboardButton("🟢 Low Priority", callback_data="filter_low")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_plan_actions_keyboard(plan_id):
    """Get keyboard for plan actions"""
    keyboard = [
        [InlineKeyboardButton("✅ Toggle Complete", callback_data=f"toggle_{plan_id}")],
        [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{plan_id}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_priority_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔴 High", callback_data="priority_high")],
        [InlineKeyboardButton("🟡 Medium", callback_data="priority_medium")],
        [InlineKeyboardButton("🟢 Low", callback_data="priority_low")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_plan_details_keyboard(plan_id):
    keyboard = [
        [InlineKeyboardButton("✅ Toggle Complete", callback_data=f"toggle_{plan_id}")],
        [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{plan_id}")],
        [InlineKeyboardButton("📋 All Plans", callback_data="plans")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Initialize user session
    user_id = str(user.id)
    user_sessions[user_id] = {}
    
    welcome_message = (
        f"📋 Welcome {user.first_name} to **PlanMakerBot**!\n\n"
        "Your personal planning companion!\n\n"
        "**✨ Features:**\n"
        "• 📋 Create and manage plans\n"
        "• 📝 Add tasks to plans\n"
        "• 🎯 Set priorities (High, Medium, Low)\n"
        "• 📅 Set due dates\n"
        "• 📊 Filter plans by status/priority\n"
        "• ✅ Track completed tasks\n\n"
        "**🎯 Quick Start:**\n"
        "• Click 'New Plan' to create your first plan\n"
        "• Click 'My Plans' to view all plans\n"
        "• Use filters to organize your plans\n\n"
        "⬇️ Start planning now!"
    )
    
    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **PlanMakerBot User Guide**\n\n"
        "**📋 My Plans**\n"
        "• View all your plans\n"
        "• Toggle completion status\n"
        "• Delete plans\n\n"
        "**➕ New Plan**\n"
        "• Enter plan title\n"
        "• Add tasks (one per line)\n"
        "• Set priority\n"
        "• Set due date (optional)\n\n"
        "**📊 Filter Plans**\n"
        "• All plans\n"
        "• Active (incomplete)\n"
        "• Completed\n"
        "• By priority (High/Medium/Low)\n\n"
        "**📝 Today's Tasks**\n"
        "• View tasks due today\n\n"
        "**Commands**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/newplan - Create a new plan\n"
        "/plans - View all plans\n"
        "/today - View today's tasks"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def new_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newplan command"""
    await update.message.reply_text(
        "➕ **Create a New Plan**\n\n"
        "Please enter the plan title:\n\n"
        "Example: `Weekend Trip Planning`",
        parse_mode="Markdown"
    )
    user_id = str(update.effective_user.id)
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["action"] = "new_plan_title"

async def plans_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /plans command"""
    user_id = str(update.effective_user.id)
    plans = get_plans(user_id)
    
    if not plans:
        await update.message.reply_text(
            "📋 **No plans yet!**\n\n"
            "Create your first plan with /newplan",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    result = format_plans_list(plans)
    await update.message.reply_text(
        result,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today command"""
    user_id = str(update.effective_user.id)
    plans = get_plans(user_id, "active")
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_plans = [p for p in plans if p.get("due_date") == today]
    
    if not today_plans:
        await update.message.reply_text(
            "📝 **No tasks due today!**\n\n"
            "Enjoy your day! 🎉",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    result = format_plans_list(today_plans, "📝 Today's Tasks")
    await update.message.reply_text(
        result,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    
    if data == "plans":
        plans = get_plans(user_id)
        if not plans:
            await query.edit_message_text(
                "📋 **No plans yet!**\n\n"
                "Create your first plan with 'New Plan' button below.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        result = format_plans_list(plans)
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "new":
        await query.edit_message_text(
            "➕ **Create a New Plan**\n\n"
            "Please enter the plan title:\n\n"
            "Example: `Weekend Trip Planning`",
            parse_mode="Markdown"
        )
        user_sessions[user_id]["action"] = "new_plan_title"
    
    elif data == "filter":
        await query.edit_message_text(
            "📊 **Filter Plans**\n\n"
            "Choose a filter option:",
            parse_mode="Markdown",
            reply_markup=get_filter_keyboard()
        )
    
    elif data.startswith("filter_"):
        filter_type = data.replace("filter_", "")
        plans = get_plans(user_id, filter_type)
        
        filter_names = {
            "all": "All Plans",
            "active": "Active Plans",
            "completed": "Completed Plans",
            "high": "High Priority",
            "medium": "Medium Priority",
            "low": "Low Priority"
        }
        
        if not plans:
            await query.edit_message_text(
                f"📋 **No {filter_names.get(filter_type, 'filtered')}**\n\n"
                "Try a different filter or create a new plan!",
                parse_mode="Markdown",
                reply_markup=get_filter_keyboard()
            )
            return
        
        result = format_plans_list(plans, f"📋 {filter_names.get(filter_type, 'Filtered Plans')}")
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=get_filter_keyboard()
        )
    
    elif data == "today":
        plans = get_plans(user_id, "active")
        today = datetime.now().strftime("%Y-%m-%d")
        today_plans = [p for p in plans if p.get("due_date") == today]
        
        if not today_plans:
            await query.edit_message_text(
                "📝 **No tasks due today!**\n\n"
                "Enjoy your day! 🎉",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        result = format_plans_list(today_plans, "📝 Today's Tasks")
        await query.edit_message_text(
            result,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data.startswith("toggle_"):
        plan_id = int(data.replace("toggle_", ""))
        if toggle_plan_completion(user_id, plan_id):
            plans = get_plans(user_id)
            result = format_plans_list(plans)
            await query.edit_message_text(
                result,
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ **Plan not found**",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    
    elif data.startswith("delete_"):
        plan_id = int(data.replace("delete_", ""))
        if delete_plan(user_id, plan_id):
            plans = get_plans(user_id)
            if not plans:
                await query.edit_message_text(
                    "🗑️ **Plan deleted successfully!**\n\n"
                    "No plans left. Create a new one!",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            else:
                result = format_plans_list(plans)
                await query.edit_message_text(
                    "🗑️ **Plan deleted successfully!**\n\n" + result,
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
        else:
            await query.edit_message_text(
                "❌ **Plan not found**",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    
    elif data.startswith("priority_"):
        priority = data.replace("priority_", "")
        user_sessions[user_id]["priority"] = priority
        await query.edit_message_text(
            f"✅ Priority set to **{priority.title()}**\n\n"
            "Now enter the due date (optional) or skip:\n"
            "Format: `YYYY-MM-DD` or type `skip`",
            parse_mode="Markdown"
        )
        user_sessions[user_id]["action"] = "new_plan_due_date"
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to plan?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        user_sessions[user_id]["action"] = None

# ==================== MESSAGE HANDLERS ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    
    action = user_sessions[user_id].get("action", "")
    
    if action == "new_plan_title":
        user_sessions[user_id]["plan_title"] = text
        user_sessions[user_id]["action"] = "new_plan_tasks"
        
        await update.message.reply_text(
            f"📝 **Plan Title:** {text}\n\n"
            "Now enter your tasks (one per line):\n\n"
            "Example:\n"
            "`- Research destinations`\n"
            "`- Book flights`\n"
            "`- Find accommodation`\n\n"
            "Send `skip` if you have no tasks yet.",
            parse_mode="Markdown"
        )
    
    elif action == "new_plan_tasks":
        tasks = []
        if text.lower() != "skip":
            tasks = [t.strip("- ").strip() for t in text.split('\n') if t.strip()]
        
        user_sessions[user_id]["tasks"] = tasks
        user_sessions[user_id]["action"] = "new_plan_priority"
        
        await update.message.reply_text(
            f"📝 **Tasks:** {len(tasks)} tasks added\n\n"
            "Now select priority level:",
            parse_mode="Markdown",
            reply_markup=get_priority_keyboard()
        )
    
    elif action == "new_plan_due_date":
        due_date = None
        if text.lower() != "skip":
            try:
                datetime.strptime(text, "%Y-%m-%d")
                due_date = text
            except ValueError:
                await update.message.reply_text(
                    "❌ **Invalid date format**\n\n"
                    "Please use format: `YYYY-MM-DD`\n"
                    "Example: `2024-12-31`\n\n"
                    "Or type `skip` to skip due date.",
                    parse_mode="Markdown"
                )
                return
        
        # Create the plan
        title = user_sessions[user_id].get("plan_title", "Untitled")
        tasks = user_sessions[user_id].get("tasks", [])
        priority = user_sessions[user_id].get("priority", "medium")
        
        plan = create_plan(user_id, title, tasks, priority, due_date)
        
        # Clear session
        user_sessions[user_id] = {}
        
        # Format response
        response = f"✅ **Plan Created Successfully!**\n\n"
        response += f"📋 **Title:** {title}\n"
        response += f"📝 **Tasks:** {len(tasks)} tasks\n"
        response += f"🎯 **Priority:** {priority.title()}\n"
        if due_date:
            response += f"📅 **Due:** {due_date}\n"
        response += f"📊 **Plan ID:** #{plan['id']}\n\n"
        response += "💡 Use /plans to view all your plans!"
        
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    else:
        # Default response
        await update.message.reply_text(
            "👋 **Use the buttons below to manage your plans!**\n\n"
            "I can help you:\n"
            "• 📋 Create and track plans\n"
            "• 📝 Manage tasks\n"
            "• 🎯 Set priorities\n"
            "• 📅 Set due dates\n\n"
            "Click 'New Plan' to get started!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    print("📋 Starting PlanMakerBot...")
    print("📝 Ready to help you plan!")
    
    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("newplan", new_plan_command))
    application.add_handler(CommandHandler("plans", plans_command))
    application.add_handler(CommandHandler("today", today_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
