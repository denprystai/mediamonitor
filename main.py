import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Global dictionary to store keywords and monitored news
user_keywords = {}
user_saved_news = {}
user_monitoring_frequency = {}

# Command to start the bot
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Welcome! Use /addkeyword to add a keyword for news monitoring.")

# Command to add a keyword for monitoring
def add_keyword(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    keyword = " ".join(context.args)

    if not keyword:
        update.message.reply_text("Please provide a keyword after the command. Example: /addkeyword technology")
        return

    if user_id not in user_keywords:
        user_keywords[user_id] = []

    user_keywords[user_id].append(keyword)
    update.message.reply_text(f"Keyword '{keyword}' has been added for monitoring.")

# Command to list all monitored keywords
def list_keywords(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    keywords = user_keywords.get(user_id, [])

    if not keywords:
        update.message.reply_text("You don't have any keywords being monitored.")
    else:
        update.message.reply_text(f"Your monitored keywords: {', '.join(keywords)}")

# Command to delete a keyword
def delete_keyword(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    keyword = " ".join(context.args)

    if not keyword:
        update.message.reply_text("Please provide a keyword to delete. Example: /deletekeyword technology")
        return

    if user_id in user_keywords and keyword in user_keywords[user_id]:
        user_keywords[user_id].remove(keyword)
        update.message.reply_text(f"Keyword '{keyword}' has been deleted from monitoring.")
    else:
        update.message.reply_text(f"Keyword '{keyword}' not found in your monitored list.")

# Command to display saved news
def saved_news(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    saved = user_saved_news.get(user_id, [])

    if not saved:
        update.message.reply_text("You don't have any saved news.")
    else:
        for news in saved:
            update.message.reply_photo(photo=news['image'], caption=f"Title: {news['title']}\nSummary: {news['summary']}\nSource: {news['url']}")

# Command to set monitoring frequency
def set_frequency(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    try:
        frequency = int(context.args[0])
        if frequency < 1:
            update.message.reply_text("Please provide a valid frequency in hours (minimum 1 hour).")
            return
        user_monitoring_frequency[user_id] = frequency
        update.message.reply_text(f"Monitoring frequency set to every {frequency} hour(s).")
    except (IndexError, ValueError):
        update.message.reply_text("Please provide a valid frequency in hours. Example: /setfrequency 3")

# Function to save interesting news
def save_news(user_id, news):
    if user_id not in user_saved_news:
        user_saved_news[user_id] = []
    user_saved_news[user_id].append(news)

# Monitor news based on keywords
def monitor_news(context: CallbackContext) -> None:
    for user_id, keywords in user_keywords.items():
        frequency = user_monitoring_frequency.get(user_id, 1)
        for keyword in keywords:
            response = requests.get(f'https://newsapi.org/v2/everything?q={keyword}&language=en&apiKey=YOUR_NEWSAPI_KEY')
            news_items = response.json().get('articles', [])
            
            for item in news_items[:3]:  # Limit to first 3 articles
                news = {
                    'title': item['title'],
                    'summary': item['description'],
                    'url': item['url'],
                    'image': item['urlToImage']
                }
                
                # Send news to user
                context.bot.send_photo(chat_id=user_id, photo=news['image'], caption=f"Title: {news['title']}\nSummary: {news['summary']}\nSource: {news['url']}")
                
                # Inline button to save the news
                keyboard = [[InlineKeyboardButton("Save", callback_data=json.dumps(news))]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(chat_id=user_id, text="Do you want to save this news?", reply_markup=reply_markup)

# Handle callback queries for saving news
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    news = json.loads(query.data)
    user_id = query.message.chat_id
    save_news(user_id, news)

    query.edit_message_text(text=f"Saved: {news['title']}")

# Command to provide summary of saved news (daily or weekly)
def summary(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    saved = user_saved_news.get(user_id, [])

    if not saved:
        update.message.reply_text("You don't have any saved news.")
    else:
        summary_text = "Summary of your saved news:\n"
        for news in saved:
            summary_text += f"- {news['title']}: {news['url']}\n"
        update.message.reply_text(summary_text)

# Main function to start the bot
def main() -> None:
    updater = Updater("YOUR_TELEGRAM_BOT_TOKEN")

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("addkeyword", add_keyword))
    dispatcher.add_handler(CommandHandler("listkeywords", list_keywords))
    dispatcher.add_handler(CommandHandler("deletekeyword", delete_keyword))
    dispatcher.add_handler(CommandHandler("savednews", saved_news))
    dispatcher.add_handler(CommandHandler("setfrequency", set_frequency))
    dispatcher.add_handler(CommandHandler("summary", summary))
    dispatcher.add_handler(CallbackQueryHandler(button))

    # Job queue to monitor news periodically (e.g., every hour)
    job_queue = updater.job_queue
    job_queue.run_repeating(monitor_news, interval=3600, first=10)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
