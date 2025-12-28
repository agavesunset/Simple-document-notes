import sys
import os
import re
import datetime
import tkinter as tk
from tkinter import font, messagebox, ttk

# --- 配置区 ---
STREAM_NAME = "UserNotes"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"

# 正则表达式：用于识别 "--- YYYY-MM-DD HH:MM ---" 这样的分隔符
# 捕获组1是时间，捕获组2是内容（非贪婪匹配，直到下一个分隔符或字符串结束）
SPLIT_PATTERN = r'(--- \d{4}-\d{2}-\d{2} \d{2}:\d{2} ---)\r?\n'

def get_ads(file_path):
    stream_path = f"{file_path}:{STREAM_NAME}"
    try:
        with open(stream_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeError:
        try:
            with open(stream_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except OSError:
            return ""
    except OSError:
        return ""

def write_ads(file_path, content):
    stream_path = f"{file_path}:{STREAM_NAME}"
    try:
        if not content or content.strip() == "":
            try:
                os.remove(stream_path)
            except FileNotFoundError:
                return True
        else:
            with open(stream_path, 'w', encoding='utf-8') as f:
                f.write(content)
        return True
    except (OSError, UnicodeError):
        return False

# --- 解析器：把长文本切分成列表 ---
def parse_notes(raw_text):
    """
    输入：长字符串
    输出：[{'header': '--- 时间 ---', 'body': '内容'}, ...]
    """
    if not raw_text:
        return []
    
    # 使用正则切分，保留分隔符
    parts = re.split(SPLIT_PATTERN, raw_text)
    # parts[0] 可能是空白（如果开头就是分隔符），parts[1]是时间，parts[2]是内容...
    
    entries = []
    # 过滤掉开头的空字符串
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    elif parts and "---" not in parts[0]: 
        # 如果开头不是时间戳（比如老数据），把它当做第一条无头记录
        entries.append({'header': '--- 旧数据 ---', 'body': parts[0].strip()})
        parts = parts[1:]

    # 成对处理 (Header + Body)
    for i in range(0, len(parts) - 1, 2):
        header = parts[i].strip()
        body = parts[i + 1].strip()
        entries.append({'header': header, 'body': body})

    if len(parts) % 2 == 1:
        header = parts[-1].strip()
        if header:
            entries.append({'header': header, 'body': ""})
        
    return entries

# --- GUI 类 ---
class NoteManagerApp:
    def __init__(self, root, file_path, raw_text):
        self.root = root
        self.file_path = file_path
        self.entries = parse_notes(raw_text) # 解析现有数据
        self.filename = os.path.basename(file_path)
        self.dirty = False
        self.last_deleted = None
        self._resize_job = None
        self.default_font = font.nametofont("TkDefaultFont")
        self.header_font = self.default_font.copy()
        self.header_font.configure(size=max(self.default_font.cget("size") - 1, 8))
        
        # 窗口设置
        self.root.title(f"SpaceM_Mark - {self.filename}")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(600, int(screen_width * 0.6))
        height = min(700, int(screen_height * 0.7))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(480, 500)
        self.root.attributes('-topmost', True) 
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # === 1. 历史记录区域 (可滚动) ===
        # 创建一个 Canvas + Scrollbar 结构来实现滚动
        self.canvas = tk.Canvas(root, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=480)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 布局滚动区
        self.canvas.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        self.scrollbar.place(relx=1, rely=0, relheight=1, anchor="ne")

        # === 2. 底部输入区 ===
        bottom_frame = ttk.Frame(root)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        ttk.Label(bottom_frame, text="追加新备注:").pack(anchor="w")
        self.new_note_entry = tk.Text(bottom_frame, height=4)
        self.new_note_entry.pack(fill="x", pady=5)
        self.new_note_entry.edit_modified(False)
        self.new_note_entry.bind("<<Modified>>", self._on_note_modified)
        
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill="x")
        self.undo_btn = ttk.Button(btn_frame, text="撤销删除", command=self.undo_delete, state="disabled")
        self.undo_btn.pack(side="left")
        ttk.Button(btn_frame, text="保存 (Save)", command=self.save_and_exit).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="取消 (Cancel)", command=root.destroy).pack(side="right")

        # === 3. 渲染历史列表 ===
        self.refresh_ui()

        # 鼠标滚轮支持
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.root.bind("<Configure>", self._on_resize)

    def _bind_mousewheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_resize(self, _event):
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self._apply_resize)

    def _apply_resize(self):
        self._resize_job = None
        self.refresh_ui()

    def _on_note_modified(self, _event):
        if self.new_note_entry.edit_modified():
            self.dirty = True
            self.new_note_entry.edit_modified(False)

    def _on_mousewheel(self, event):
        if hasattr(event, "num") and event.num in (4, 5):
            delta = -1 if event.num == 4 else 1
        else:
            delta = int(-1 * (event.delta / 120))
        self.canvas.yview_scroll(delta, "units")

    def _on_close(self):
        has_text = self.new_note_entry.get("1.0", "end").strip()
        if self.dirty or has_text:
            if not messagebox.askyesno("未保存", "有未保存的内容，确定退出吗？"):
                return
        self.root.destroy()

    def refresh_ui(self):
        # 清空旧控件
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.entries:
            lbl = ttk.Label(self.scrollable_frame, text="(暂无备注)", foreground="gray")
            lbl.pack(pady=20)
            return

        # 重新生成每一行
        for idx, item in enumerate(self.entries):
            # 每一条是一个 Frame
            row_frame = ttk.Frame(self.scrollable_frame, relief="groove", borderwidth=1)
            row_frame.pack(fill="x", pady=5, padx=2)

            # 头部：时间和删除按钮
            header_frame = ttk.Frame(row_frame)
            header_frame.pack(fill="x", padx=5, pady=2)
            
            # 时间标签
            ttk.Label(header_frame, text=item['header'], foreground="blue", font=self.header_font).pack(side="left")
            
            btn_group = ttk.Frame(header_frame)
            btn_group.pack(side="right")

            edit_btn = tk.Button(
                btn_group,
                text="✏️",
                command=lambda i=idx: self.edit_entry(i),
                relief="flat",
                fg="black",
                cursor="hand2",
                font=self.header_font
            )
            edit_btn.pack(side="left", padx=(0, 4))

            # 删除按钮 (使用 partial 或 closure 绑定 index)
            # 注意：这里直接传 idx 是安全的，因为每次都会全部重绘
            del_btn = tk.Button(
                btn_group,
                text="❌",
                command=lambda i=idx: self.delete_entry(i),
                relief="flat",
                fg="red",
                cursor="hand2",
                font=self.header_font
            )
            del_btn.pack(side="left")

            # 内容
            wraplength = max(self.root.winfo_width() - 80, 300)
            content_lbl = tk.Label(row_frame, text=item['body'], justify="left", anchor="w", wraplength=wraplength)
            content_lbl.pack(fill="x", padx=5, pady=(0, 5))

    def delete_entry(self, index):
        # 简单直接：从列表删掉，然后重绘 UI
        if messagebox.askyesno("确认", "确定删除这条记录吗？"):
            self.last_deleted = (index, self.entries[index])
            del self.entries[index]
            self.dirty = True
            self.undo_btn.config(state="normal")
            self.refresh_ui()

    def undo_delete(self):
        if not self.last_deleted:
            return
        index, entry = self.last_deleted
        index = min(index, len(self.entries))
        self.entries.insert(index, entry)
        self.last_deleted = None
        self.undo_btn.config(state="disabled")
        self.dirty = True
        self.refresh_ui()

    def edit_entry(self, index):
        entry = self.entries[index]
        edit_win = tk.Toplevel(self.root)
        edit_win.title("编辑备注")
        edit_win.transient(self.root)
        edit_win.grab_set()

        header_label = ttk.Label(edit_win, text=entry["header"], foreground="blue", font=self.header_font)
        header_label.pack(anchor="w", padx=10, pady=(10, 4))

        text_box = tk.Text(edit_win, height=8, wrap="word")
        text_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        text_box.insert("1.0", entry["body"])

        btn_frame = ttk.Frame(edit_win)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        def save_edit():
            new_body = text_box.get("1.0", "end").strip()
            self.entries[index]["body"] = new_body
            self.dirty = True
            self.refresh_ui()
            edit_win.destroy()

        ttk.Button(btn_frame, text="保存", command=save_edit).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="取消", command=edit_win.destroy).pack(side="right")

    def save_and_exit(self):
        # 1. 收集剩下的历史记录
        segments = []
        for item in self.entries:
            segments.append(f"{item['header']}\n{item['body']}".strip())
        
        # 2. 收集新输入的
        new_text = self.new_note_entry.get("1.0", "end").strip()
        if new_text:
            time_header = f"--- {datetime.datetime.now().strftime(TIMESTAMP_FORMAT)} ---"
            segments.append(f"{time_header}\n{new_text}")
            
        # 3. 去掉尾部多余换行并保存
        final_content = "\n\n".join(segment for segment in segments if segment).strip()
        if write_ads(self.file_path, final_content):
            self.root.destroy() # 成功关闭
        else:
            messagebox.showerror("错误", "写入失败！")

# --- 主程序入口 ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit()

    target_files = sys.argv[1:]
    
    # 简单处理：如果是单文件，启动高级UI
    # 如果是批量文件，还是用简单的追加模式（因为批量没法逐个显示删除）
    
    if len(target_files) == 1:
        target = target_files[0]
        if os.path.exists(target):
            root = tk.Tk()
            # 读取当前内容
            raw_data = get_ads(target)
            app = NoteManagerApp(root, target, raw_data)
            root.mainloop()
        else:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("错误", f"文件不存在：{target}")
            root.destroy()
            
    else:
        # === 批量模式（保持原样，只负责追加）===
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        prompt_text = f"【批量模式】\n你选中了 {len(target_files)} 个对象。\n\n请输入要统一追加的备注:"
        # 这里为了简单，还是临时用回 simpledialog，或者你需要这里也做一个弹窗
        # 为了不引入额外import，这里简单处理
        from tkinter import simpledialog
        input_note = simpledialog.askstring(f"SpaceM_Mark (批量)", prompt_text)
        
        if input_note and input_note.strip():
            if not messagebox.askyesno(
                "确认批量追加",
                f"将把以下内容追加到 {len(target_files)} 个文件：\n\n{input_note}"
            ):
                root.destroy()
                sys.exit()
            time_header = f"--- {datetime.datetime.now().strftime(TIMESTAMP_FORMAT)} ---"
            count = 0
            failed = []
            for f in target_files:
                current = get_ads(f)
                prefix = "\n\n" if current else ""
                new_c = f"{current}{prefix}{time_header}\n{input_note}"
                if write_ads(f, new_c):
                    count += 1
                else:
                    failed.append(f)
            if failed:
                messagebox.showwarning(
                    "部分失败",
                    f"成功追加 {count} 个文件，失败 {len(failed)} 个：\n"
                    + "\n".join(failed)
                )
            else:
                messagebox.showinfo("完成", f"已追加 {count} 个文件。")
        root.destroy()
