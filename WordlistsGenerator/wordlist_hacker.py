import random
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk

running = False
boot_done = False
generated_lines = []
seen = set()

symbols = ["!", "@", "#", "$", "%", "&", "*", "_", "-", "+", "?", ".", "~", "^"]
common_numbers = [
    "1", "12", "123", "1234", "12345", "123456",
    "007", "69", "666", "777", "0", "00", "1980", "1990",
    "2000", "2010", "2020", "2021", "2022", "2023", "2024", "2025", "2026"
]
extra_words = [
    "admin", "root", "user", "login", "pass", "love", "god", "master",
    "king", "queen", "boss", "real", "official", "666", "xd", "pro",
    "gamer", "dark", "shadow", "ghost", "fire", "666", "vip"
]
leet_map = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "b": "8"}

GLITCH_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&*"
MATRIX_CHARS = "アカサタナハマヤラワ0123456789!@#$%&ABCDEFGHIJKLMNOPQRSTUVWXYZ"

BOOT_LINES = [
    "[ WORDLIST ENGINE BOOT ]",
    "> Loading mutation engine (case, leetspeak, reverse)... [OK]",
    "> Loading symbol & number affix tables.................. [OK]",
    "> Indexing OSINT fields (name, pet, birth date, nick)... [OK]",
    "> Compiling combination matrix.......................... [OK]",
    "> Linking Hashcat rule generator........................ [OK]",
    "> Deduplication engine ready............................ [OK]",
    "",
    "ENGINE READY.",
]

ASCII_BANNER = r"""
 __        __            _ _ _     _
 \ \      / /__  _ __ __| | (_)___| |_
  \ \ /\ / / _ \| '__/ _` | | / __| __|
   \ V  V / (_) | | | (_| | | \__ \ |_
    \_/\_/ \___/|_|  \__,_|_|_|___/\__|
        W O R D L I S T   E N G I N E
"""


def apply_leet(word):
    return "".join(leet_map.get(c.lower(), c) for c in word)


def reverse_word(word):
    return word[::-1]


def date_tokens(date_str):
    digits_only = "".join(c for c in date_str if c.isdigit())
    tokens = set()

    if not digits_only:
        return []

    tokens.add(digits_only)

    if len(digits_only) == 8:
        dd, mm, yyyy = digits_only[0:2], digits_only[2:4], digits_only[4:8]
        yy = yyyy[2:]
        tokens.update({
            dd, mm, yyyy, yy,
            dd + mm, mm + dd,
            dd + mm + yyyy, mm + dd + yyyy, yyyy + mm + dd,
            dd + mm + yy, mm + dd + yy, yy + mm + dd,
        })
    elif len(digits_only) == 4:
        tokens.add(digits_only[2:])

    return list(tokens)


def word_variants(base):
    return list(dict.fromkeys([
        base,
        base.lower(),
        base.upper(),
        base.capitalize(),
        reverse_word(base),
        reverse_word(base.capitalize()),
        base + base,
        apply_leet(base),
        apply_leet(base.lower()),
        apply_leet(base.upper()),
        apply_leet(base.capitalize()),
    ]))


def build_pools(base, extra_words_input=None, extra_numbers_input=None):
    variants = word_variants(base)
    numbers_base = list(dict.fromkeys(common_numbers + (extra_numbers_input or [])))
    numbers_full = list(dict.fromkeys(numbers_base + [str(n) for n in range(0, 1000)]))
    words_pool = list(dict.fromkeys(extra_words + (extra_words_input or [])))

    mixed_affixes = list(dict.fromkeys(
        symbols
        + numbers_base
        + [s + n for s in symbols for n in numbers_base]
        + [n + s for s in symbols for n in numbers_base]
        + [s1 + s2 for s1 in symbols for s2 in symbols]
        + [s1 + n + s2 for s1 in symbols for n in numbers_base for s2 in symbols]
    ))

    return variants, numbers_base, numbers_full, words_pool, mixed_affixes


def estimate_total(base, extra_words_input=None, extra_numbers_input=None):
    variants, numbers_base, numbers_full, words_pool, mixed_affixes = build_pools(
        base, extra_words_input, extra_numbers_input
    )
    v = len(variants)

    total = v
    total += v * len(numbers_full) * 2
    total += v * len(symbols) * 2 + v * len(symbols) * len(symbols)
    total += v * len(words_pool) * 2
    total += v * len(symbols) * len(numbers_full) * 2
    total += v * len(words_pool) * len(numbers_full) * 2
    total += v * len(mixed_affixes) * 3

    return total


def generate_all_combinations(base, extra_words_input=None, extra_numbers_input=None):
    variants, numbers_base, numbers_full, words_pool, mixed_affixes = build_pools(
        base, extra_words_input, extra_numbers_input
    )

    for v in variants:
        yield v

    for v in variants:
        for n in numbers_full:
            yield v + n
            yield n + v

    for v in variants:
        for s in symbols:
            yield v + s
            yield s + v
            for s2 in symbols:
                yield s + v + s2

    for v in variants:
        for e in words_pool:
            yield v + e
            yield e + v

    for v in variants:
        for s in symbols:
            for n in numbers_full:
                yield v + s + n
                yield n + s + v

    for v in variants:
        for e in words_pool:
            for n in numbers_full:
                yield e + v + n
                yield v + e + n

    for v in variants:
        for a in mixed_affixes:
            yield a + v
            yield v + a
            yield a + v + a


def process(base, extra_words_input, extra_numbers_input, total_estimate):

    global running
    counter = 0
    start_time = time.time()
    last_ui_update = 0.0

    for line in generate_all_combinations(base, extra_words_input, extra_numbers_input):

        if not running:
            break

        if line in seen:
            continue

        seen.add(line)
        generated_lines.append(line)
        counter += 1

        now = time.time()
        if now - last_ui_update >= 0.05:
            elapsed = now - start_time
            speed = counter / elapsed if elapsed > 0 else 0
            counter_label.config(text=f"{counter:,}")
            speed_label.config(text=f"{speed:,.0f} words/sec")
            if total_estimate:
                progress_bar["value"] = min(100, (counter / total_estimate) * 100)
            last_ui_update = now

        if counter % 50000 == 0:
            log.insert(tk.END, f"Generated: {counter:,}\n")
            log.see(tk.END)
    else:
        counter_label.config(text=f"{counter:,}")
        progress_bar["value"] = 100
        log.insert(tk.END, f"\n✅ All possible combinations generated ({counter:,}).\n")
        log.see(tk.END)
        running = False


def collect_osint():
    fields = [
        name_entry.get().strip(),
        lastname_entry.get().strip(),
        nickname_entry.get().strip(),
        pet_entry.get().strip(),
    ]
    extra_words_input = [f for f in fields if f]

    extra_txt = extra_entry.get().strip()
    if extra_txt:
        extra_words_input += [p.strip() for p in extra_txt.split(",") if p.strip()]

    extra_numbers_input = date_tokens(date_entry.get().strip())

    return extra_words_input, extra_numbers_input


def start():
    global running
    if not running:
        base = word_entry.get().strip()
        if not base:
            log.insert(tk.END, "\n⚠️ Type a word before starting.\n")
            log.see(tk.END)
            return

        extra_words_input, extra_numbers_input = collect_osint()

        generated_lines.clear()
        seen.clear()
        counter_label.config(text="0")
        speed_label.config(text="0 words/sec")
        progress_bar["value"] = 0

        log.insert(tk.END, f"\n▶ Generating combinations for: {base}\n")
        if extra_words_input:
            log.insert(tk.END, f"   + OSINT data: {', '.join(extra_words_input)}\n")
        if extra_numbers_input:
            log.insert(tk.END, f"   + dates: {', '.join(extra_numbers_input)}\n")
        log.see(tk.END)

        total_estimate = estimate_total(base, extra_words_input, extra_numbers_input)

        running = True
        thread = threading.Thread(
            target=process, args=(base, extra_words_input, extra_numbers_input, total_estimate)
        )
        thread.start()


def stop():
    global running
    running = False
    save_file()


def save_file():

    path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text file", "*.txt")],
        title="Save wordlist"
    )

    if path:
        with open(path, "w", encoding="utf-8") as f:
            for line in generated_lines:
                f.write(line + "\n")

        log.insert(tk.END, f"\n✅ Saved to: {path}\n")
        log.insert(tk.END, f"   hashcat -a 0 -m <mode> hash.txt \"{path}\"\n")
        log.insert(tk.END, f"   john --wordlist=\"{path}\" hash.txt\n")
        log.see(tk.END)


def generate_hashcat_rules():

    rules = [":", "l", "u", "c", "t", "r", "d"]

    for s in symbols:
        rules.append(f"${s}")
        rules.append(f"^{s}")

    for n in common_numbers:
        rules.append("".join(f"${c}" for c in n))
        rules.append("".join(f"^{c}" for c in reversed(n)))

    leet_rule = " ".join(f"s{k}{v}" for k, v in leet_map.items())
    rules.append(leet_rule)
    rules.append("c " + leet_rule)
    rules.append("u " + leet_rule)

    for s in symbols:
        rules.append(f"c ${s}")
        rules.append(leet_rule + f" ${s}")

    for n in common_numbers:
        suffix = "".join(f"${c}" for c in n)
        rules.append("c " + suffix)
        rules.append(leet_rule + " " + suffix)

    return list(dict.fromkeys(rules))


def export_hashcat_rules():

    path = filedialog.asksaveasfilename(
        defaultextension=".rule",
        filetypes=[("Hashcat rule", "*.rule")],
        title="Save Hashcat rules"
    )

    if path:
        rules = generate_hashcat_rules()
        with open(path, "w", encoding="utf-8") as f:
            for r in rules:
                f.write(r + "\n")

        log.insert(tk.END, f"\n✅ {len(rules)} Hashcat rules saved to: {path}\n")
        log.insert(tk.END, f"   hashcat -a 0 -m <mode> hash.txt wordlist.txt -r \"{path}\"\n")
        log.see(tk.END)


def animate_matrix():
    matrix_canvas.delete("all")
    for y in range(0, 90, 4):
        matrix_canvas.create_line(0, y, 760, y, fill="#002200")
    for drop in matrix_drops:
        char = random.choice(MATRIX_CHARS)
        matrix_canvas.create_text(drop[0], drop[1], text=char, fill="lime", font=("Courier", 12))
        drop[1] += 14
        if drop[1] > 90:
            drop[1] = random.randint(-120, 0)
    window.after(80, animate_matrix)


def start_matrix():
    columns = 760 // 14
    for i in range(columns):
        x = i * 14 + 4
        y = random.randint(-200, 0)
        matrix_drops.append([x, y])
    animate_matrix()


def decode_intro(steps_left, final_text):
    if steps_left <= 0:
        title_label.config(text=final_text)
        return

    glitched = "".join(
        c if c == " " or random.random() < (1 - steps_left / 30) else random.choice(GLITCH_CHARS)
        for c in final_text
    )
    title_label.config(text=glitched)
    window.after(40, decode_intro, steps_left - 1, final_text)


window = tk.Tk()
window.title("Hacker Wordlist Generator")
window.configure(bg="black")
window.geometry("780x760")

main_frame = tk.Frame(window, bg="black")

title_label = tk.Label(
    main_frame,
    text="WORDLIST GENERATOR",
    fg="lime",
    bg="black",
    font=("Courier", 22, "bold")
)
title_label.pack(pady=(10, 5))

matrix_canvas = tk.Canvas(main_frame, width=760, height=90, bg="black", highlightthickness=0)
matrix_canvas.pack(pady=(0, 5))
matrix_drops = []

word_entry = tk.Entry(
    main_frame,
    font=("Courier", 16),
    bg="black",
    fg="lime",
    insertbackground="lime"
)
word_entry.pack(pady=10)

osint_frame = tk.Frame(main_frame, bg="black")
osint_frame.pack(pady=5)

tk.Label(
    osint_frame,
    text="OSINT DATA (optional)",
    fg="lime",
    bg="black",
    font=("Courier", 12)
).grid(row=0, column=0, columnspan=2, pady=(0, 5))


def _osint_field(row, label_text):
    tk.Label(
        osint_frame, text=label_text, fg="lime", bg="black", font=("Courier", 10)
    ).grid(row=row, column=0, sticky="e", padx=5, pady=2)
    field = tk.Entry(
        osint_frame, font=("Courier", 11), bg="black", fg="lime", insertbackground="lime", width=30
    )
    field.grid(row=row, column=1, padx=5, pady=2)
    return field


name_entry = _osint_field(1, "Name:")
lastname_entry = _osint_field(2, "Last name:")
nickname_entry = _osint_field(3, "Nickname:")
pet_entry = _osint_field(4, "Pet:")
date_entry = _osint_field(5, "Birth date (DDMMYYYY):")
extra_entry = _osint_field(6, "Extra (comma separated):")

buttons_frame = tk.Frame(main_frame, bg="black")
buttons_frame.pack(pady=8)

btn_start = tk.Button(
    buttons_frame,
    text="START",
    command=start,
    bg="black",
    fg="lime",
    font=("Courier", 14)
)
btn_start.grid(row=0, column=0, padx=5)

btn_stop = tk.Button(
    buttons_frame,
    text="STOP & SAVE",
    command=stop,
    bg="black",
    fg="red",
    font=("Courier", 14)
)
btn_stop.grid(row=0, column=1, padx=5)

btn_rules = tk.Button(
    buttons_frame,
    text="EXPORT HASHCAT RULES",
    command=export_hashcat_rules,
    bg="black",
    fg="cyan",
    font=("Courier", 14)
)
btn_rules.grid(row=0, column=2, padx=5)

stats_frame = tk.Frame(main_frame, bg="black")
stats_frame.pack(pady=(5, 5), fill="x", padx=20)

counter_label = tk.Label(stats_frame, text="0", fg="lime", bg="black", font=("Courier", 30, "bold"))
counter_label.pack()

speed_label = tk.Label(stats_frame, text="0 words/sec", fg="cyan", bg="black", font=("Courier", 12))
speed_label.pack()

style = ttk.Style()
style.theme_use("default")
style.configure(
    "Matrix.Horizontal.TProgressbar",
    troughcolor="black",
    background="lime",
    bordercolor="black",
    lightcolor="lime",
    darkcolor="lime",
)

progress_bar = ttk.Progressbar(
    stats_frame, style="Matrix.Horizontal.TProgressbar", length=700, mode="determinate", maximum=100
)
progress_bar.pack(pady=5)

log = tk.Text(
    main_frame,
    bg="black",
    fg="lime",
    font=("Courier", 10)
)
log.pack(expand=True, fill="both", pady=10)


def periodic_glitch():
    window.after(random.randint(4000, 9000), trigger_glitch)


def trigger_glitch():
    decode_intro(8, "WORDLIST GENERATOR")
    periodic_glitch()


def finish_boot():
    global boot_done
    if boot_done:
        return
    boot_done = True

    boot_frame.destroy()
    main_frame.pack(fill="both", expand=True)

    log.insert(tk.END, ASCII_BANNER)
    log.insert(tk.END, "\n> System ready. Type a base word and hit START.\n")
    log.see(tk.END)

    start_matrix()
    decode_intro(30, "WORDLIST GENERATOR")
    periodic_glitch()


def skip_boot(event=None):
    finish_boot()


def type_boot_sequence(line_index=0, char_index=0):
    if boot_done:
        return

    if line_index >= len(BOOT_LINES):
        window.after(500, finish_boot)
        return

    line = BOOT_LINES[line_index]

    if char_index == 0:
        boot_text.insert(tk.END, "\n")

    if char_index < len(line):
        boot_text.insert(tk.END, line[char_index])
        boot_text.see(tk.END)
        window.after(12, type_boot_sequence, line_index, char_index + 1)
    else:
        window.after(120, type_boot_sequence, line_index + 1, 0)


boot_frame = tk.Frame(window, bg="black")
boot_frame.pack(fill="both", expand=True)

boot_text = tk.Text(
    boot_frame,
    bg="black",
    fg="lime",
    font=("Courier", 13),
    bd=0,
    highlightthickness=0
)
boot_text.pack(fill="both", expand=True, padx=30, pady=30)

boot_hint = tk.Label(
    boot_frame,
    text="[ press ENTER or click to skip ]",
    fg="#227722",
    bg="black",
    font=("Courier", 9)
)
boot_hint.pack(pady=(0, 15))

boot_text.bind("<Button-1>", skip_boot)
boot_hint.bind("<Button-1>", skip_boot)
window.bind("<Return>", skip_boot)

type_boot_sequence()

window.mainloop()
