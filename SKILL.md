---
name: xhs-moment
description: "Xiaohongshu / RED moment capture — turn a brief thought, feeling, or life observation into a polished social media post with minimalist card images. Use when the user wants to post to Xiaohongshu (小红书), says 随手记/发帖/记一下/发到小红书, or gives a sentence to convert into a social post."
---

# 小红书随手记

一句话变成一条精美的小红书帖子：自动生成极简留白风配图 + 提炼文案 + 加话题 + 发布。

## Workflow

### Step 1: Parse input & detect mood

| Input type | How to detect | Action |
|------------|--------------|--------|
| A sentence | Short text, no file path | Analyze mood → select palette → full flow |
| Text + image path | Contains a file path | User image as cover, generated cards as 2-3 |
| Mood keyword | "发个治愈系帖子" etc. | AI creates content based on mood |
| Long paragraph | Multiple sentences | Extract the punchiest line for cards, condense rest as body |

### Step 2: Generate copy

Produce all of the following before generating images:

**Title** (max 20 chars):
- Emotional hook, makes people want to click
- At most 1 emoji
- Example: `被一杯咖啡治愈了`

**Body** (100-200 chars):
- Conversational XHS tone, like chatting with a friend
- Natural emoji usage, max 5
- End with engagement prompt ("你呢？")
- Avoid overly trendy slang

**Quote** (10-30 chars, rendered on image cards):
- Distilled from the user's input, punchy and standalone
- No emoji (font cannot render them)
- Prefer calm, compact phrasing. Do not overcrowd the image with text

**Topics** (3-5, comma-separated, no # prefix):
- Mix broad + niche tags
- Example: `生活感悟,治愈系,日常记录`

**Palette** (pick one):

| Palette | Mood keywords |
|---------|--------------|
| `warm` | 温暖 治愈 感恩 幸福 夕阳 |
| `cool` | 平静 思考 安静 夜晚 孤独 |
| `fresh` | 元气 春天 活力 开心 早安 |
| `elegant` | 优雅 文艺 复古 咖啡 读书 |
| `dreamy` | 浪漫 梦幻 柔软 少女 花 |
| `bold` | 力量 自信 态度 犀利 酷 |

Default to `warm` when unsure.

**Visual rules**:
- Prefer large whitespace and low information density
- Use at most 2-3 visual colors in one card
- Keep typography restrained, readable, not shouty
- Use golden-ratio composition when placing text blocks or color blocks
- If the user does not ask for a specific look, let the generator use weighted random layout selection and style-aware palette selection

### Step 3: Generate images

```bash
python3 scripts/generate.py \
  --text "quote text" \
  --subtitle "date or signature" \
  --palette auto \
  --style auto \
  --hashtags "topic1,topic2,topic3" \
  --output-dir /tmp/xhs-moment
```

> Note: the script path is relative to this skill's directory. Use the full path when invoking:
> `python3 <skill-dir>/scripts/generate.py ...`

Outputs 3 JPEG files (1080x1440):
1. **Cover** — calm headline cover, usually using golden-ratio composition
2. **Quote card** — secondary text card with more whitespace
3. **Topics card** — sparse hashtag card

Supported layout styles:
- `golden-split` — top-heavy 0.618 split, upper block large, lower area small
- `floating-card` — small text block floating in a large quiet canvas
- `quiet-corner` — text anchored near a corner / margin with strong whitespace
- `centered-balance` — centered composition around golden lines
- `ticket-stub` — restrained ticket / stub structure, more Xiaohongshu-cover-like
- `margin-label` — side label strip with a calm editorial feel
- `auto` — weighted random selection, favoring `ticket-stub` / `margin-label`, then `quiet-corner`
- Palette `auto` — weighted selection linked to style, so calmer layouts get calmer palette defaults

If the user provided an image, put their image first, generated cards after.

### Step 4: Preview

Show the user:
- Title, body text, palette chosen
- Chosen layout style
- Image file paths (use Read tool to display the cover)
- Topic tags
- Note: "默认存为草稿，说「发布」可直接发布"

Wait for confirmation. Adjust if requested.

### Step 5: Publish

```bash
npx opencli xiaohongshu publish \
  --title "title" \
  --images path1.jpg,path2.jpg,path3.jpg \
  --topics "topic1,topic2,topic3" \
  --draft true \
  "body text"
```

- Default: `--draft true` (save as draft)
- User says "直接发" / "发布" → remove `--draft true`
- Requires Chrome logged into `creator.xiaohongshu.com`
- If opencli not available, run `npx opencli doctor` to diagnose

### Note on thumbnails

After publishing, the editor may show blank image thumbnails. This is a **cosmetic frontend rendering issue only** — images are successfully uploaded to CDN and display correctly after publication. Do not attempt to fix or re-upload.
