import discord
from discord import app_commands
import os
from google import genai

# ボットの設定
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Geminiクライアント
gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ユーザーごとの会話履歴
conversation_history: dict[int, list] = {}

def ask_gemini(user_id: int, user_message: str, system_prompt: str = None) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    recent = conversation_history[user_id][-20:]

    full_prompt = (system_prompt + "\n\n" + user_message) if system_prompt else user_message

    response = gemini.models.generate_content(
model="gemini-2.0-flash",
        contents=full_prompt
    )
    reply = response.text

    conversation_history[user_id].append({
        "role": "model",
        "parts": [{"text": reply}]
    })

    return reply


@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ {client.user} としてログインしました！")


@tree.command(name="hello", description="挨拶します")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"こんにちは、{interaction.user.mention}！ 👋")

@tree.command(name="ping", description="ボットの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! レイテンシ: **{latency}ms**")

@tree.command(name="ask", description="AIに何でも質問できます")
@app_commands.describe(question="質問内容")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        reply = ask_gemini(
            interaction.user.id,
            question,
            system_prompt="あなたは親切なアシスタントです。日本語で回答してください。"
        )
        if len(reply) <= 1900:
            await interaction.followup.send(f"💬 {reply}")
        else:
            chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for i, chunk in enumerate(chunks):
                prefix = "💬 " if i == 0 else ""
                await interaction.followup.send(f"{prefix}{chunk}")
    except Exception as e:
        print(f"ERROR in ask: {type(e).__name__}: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            await interaction.followup.send("⚠️ 本日の無料利用枠が上限に達しました。明日またお試しください！")
        else:
            await interaction.followup.send(f"❌ エラーが発生しました: {e}")

@tree.command(name="script", description="スクリプトやコードを生成します")
@app_commands.describe(
    description="作りたいものの説明",
    language="プログラミング言語（例: Python, JavaScript, Bash）"
)
async def script(interaction: discord.Interaction, description: str, language: str = "Python"):
    await interaction.response.defer()
    try:
        prompt = f"{language}で以下を実装してください:\n\n{description}\n\nコードにはコメントを含めて分かりやすくしてください。"
        reply = ask_gemini(
            interaction.user.id,
            prompt,
            system_prompt=f"あなたは優秀なプログラマーです。{language}のコードを生成する際は必ずコードブロックで囲んでください。説明も日本語で行ってください。"
        )
        if len(reply) <= 1900:
            await interaction.followup.send(reply)
        else:
            chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for chunk in chunks:
                await interaction.followup.send(chunk)
    except Exception as e:
        print(f"ERROR in script: {type(e).__name__}: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            await interaction.followup.send("⚠️ 本日の無料利用枠が上限に達しました。明日またお試しください！")
        else:
            await interaction.followup.send(f"❌ エラーが発生しました: {e}")

@tree.command(name="translate", description="テキストを翻訳します")
@app_commands.describe(
    text="翻訳したいテキスト",
    target="翻訳先の言語（例: 英語, 日本語, 中国語）"
)
async def translate(interaction: discord.Interaction, text: str, target: str = "英語"):
    await interaction.response.defer()
    try:
        reply = ask_gemini(
            interaction.user.id,
            f"次のテキストを{target}に翻訳してください。翻訳結果だけを返してください:\n\n{text}",
            system_prompt="あなたは優秀な翻訳者です。翻訳結果のみを返し、余計な説明は不要です。"
        )
        embed = discord.Embed(title=f"🌐 {target}に翻訳", color=discord.Color.green())
        embed.add_field(name="原文", value=text[:500], inline=False)
        embed.add_field(name="翻訳", value=reply[:500], inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"ERROR in translate: {type(e).__name__}: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            await interaction.followup.send("⚠️ 本日の無料利用枠が上限に達しました。明日またお試しください！")
        else:
            await interaction.followup.send(f"❌ エラーが発生しました: {e}")

@tree.command(name="clear", description="会話履歴をリセットします")
async def clear(interaction: discord.Interaction):
    conversation_history.pop(interaction.user.id, None)
    await interaction.response.send_message("🗑️ 会話履歴をリセットしました！", ephemeral=True)


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("❌ 環境変数 DISCORD_TOKEN が設定されていません")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ 環境変数 GEMINI_API_KEY が設定されていません")

client.run(DISCORD_TOKEN)
