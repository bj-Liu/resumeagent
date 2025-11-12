import json
import os
import time
import threading
import tkinter as tk
import yaml
from tkinter import scrolledtext, ttk, messagebox
from HomepageDesign import HomepageDesignAgent
from PIL import ImageTk, Image
from utils import cal_cost
import asyncio
import shutil


with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)
for key, value in config.items():
    os.environ[key] = str(value)
    
class Application(tk.Tk):
    def __init__(self, agent: HomepageDesignAgent = None):
        super().__init__()

        self.title("Personal Homepage Design Agent")
        self.agent = agent
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}")
        self.configure(bg="#CCD5AE")
        self.current_page = 0
        self.pages = []


        self.title_frame = tk.Frame(self, bg='#CCD5AE')
        self.title_frame.grid(row=0, column=0, padx=10, pady=10)
       
        self.css_frame_var = tk.StringVar(value="Tailwind")
        self.agent.css_frame = "Tailwind"
        llm_type = config.get("LLM_TYPE","openai")
        if llm_type == "openai":

            self.web_design_model_options = ["gpt-4-turbo-2024-04-09","gpt-4o"]
            #self.vision_options = ["Open","Close"]
        elif llm_type == "qwen":
            self.web_design_model_options = ["qwen3-max","qwen2-72b-instruct","qwen2.5-72b-instruct"]
            #self.vision_options = ["Open", "Close"]

        style = ttk.Style()
        style.configure("Custom.TMenubutton", background="#FEFAE0")
        
        self.model_var = tk.StringVar(value=self.web_design_model_options[0])
        self.model_menu = ttk.OptionMenu(self.title_frame, self.model_var, self.web_design_model_options[0], *self.web_design_model_options, command=self.switch_model)
        self.model_menu.config(style='Custom.TMenubutton')
        self.model_menu.grid(row=0, column=1, padx=10, pady=10)
        self.model_menu_label = tk.Label(self.title_frame, text="Select Model:", bg='#CCD5AE')
        self.model_menu_label.grid(row=0, column=0, padx=10, pady=10)
        self.agent.model = self.web_design_model_options[0]

        # self.vision_var = tk.StringVar(value="Close")
        # self.vision_options = ["Open", "Close"]
        # self.vision_menu = ttk.OptionMenu(self.title_frame, self.vision_var, self.vision_options[0], *self.vision_options, command=self.switch_vision)
        # self.vision_menu.config(style='Custom.TMenubutton')
        # self.vision_menu.grid(row=0, column=3, padx=10, pady=10)
        # self.vision_menu_label = tk.Label(self.title_frame, text="Open Vision:", bg='#CCD5AE')
        # self.vision_menu_label.grid(row=0, column=2, padx=10, pady=10)

        self.is_animating = False


        self.canvas = tk.Canvas(self, width=int(screen_width) * 0.92, height=int(screen_height) * 0.85, bg='#CCD5AE')
        self.y_scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, bg='#A6B37D')
        self.x_scrollbar = tk.Scrollbar(self, orient="horizontal", command=self.canvas.xview, bg='#A6B37D')
        self.scrollable_frame = tk.Frame(self.canvas, bg='#CCD5AE')
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.y_scrollbar.set, xscrollcommand=self.x_scrollbar.set, bg='#CCD5AE')
        self.canvas.grid(row=1, column=0, padx=10, pady=10)
        self.y_scrollbar.grid(row=1, column=1, sticky="ns")
        self.x_scrollbar.grid(row=2, column=0, sticky="ew")


        self.web_design_widgets = self.create_web_design_widgets()
        self.model_menu.set_menu(self.web_design_model_options[0],*self.web_design_model_options)
        self.agent.model = self.web_design_model_options[0]
        self.display_web_design_mode()

        self.begin_time = time.time()
        with open("logs/token.json", "r") as f:
            tokens = json.load(f)
        self.begin_cost = tokens
        self.total_cost = 0
        self.time_cost = 0
        self.img_ref = None 
        
        self.backup_folder_path = None
      

    def create_web_design_widgets(self):
        web_design_widgets = {}
        web_design_widgets['input_frame'] = tk.Frame(self.scrollable_frame, width=700, bg='#CCD5AE')
        web_design_widgets['output_text'] = scrolledtext.ScrolledText(self.scrollable_frame, wrap=tk.WORD, state='normal', width=50, height=60)
        web_design_widgets['output_image_frame'] = tk.Frame(self.scrollable_frame, width=700, height=300, bg='#CCD5AE')
        web_design_widgets["input_labels"] = []
        web_design_widgets["input_entries"] = []

        language_options = ["en", "zh"]
        language_var = tk.StringVar(value="en")
        self.language_var = language_var
        language_menu = ttk.OptionMenu(web_design_widgets["input_frame"], language_var, language_options[0], *language_options, command=self.change_language)
        language_menu.config(style='Custom.TMenubutton')
        language_menu.grid(row=0, column=1, padx=10, pady=10)
        language_menu_label = tk.Label(web_design_widgets["input_frame"], text="Language:", bg='#CCD5AE')
        language_menu_label.grid(row=0, column=0, padx=10, pady=10)

        css_frame_options = ["Tailwind", "Bootstrap", "Materialize", "Bulma", "None"]
        self.css_frame_var = tk.StringVar(value="Tailwind")
        css_frame_menu = ttk.OptionMenu(web_design_widgets["input_frame"], self.css_frame_var, css_frame_options[0], *css_frame_options, command=self.on_css_frame_change)
        css_frame_menu.config(style='Custom.TMenubutton')
        css_frame_menu.grid(row=1, column=1, padx=10, pady=10)
        css_frame_menu_label = tk.Label(web_design_widgets["input_frame"], text="CSS Framework:", bg='#CCD5AE')
        css_frame_menu_label.grid(row=1, column=0, padx=10, pady=10)

        status_options = ["student", "graduate", "entry_level", "mid_level", "expert"]
        status_var = tk.StringVar(value="student")
        self.status_var = status_var
        status_menu = ttk.OptionMenu(web_design_widgets["input_frame"], status_var, status_options[0], *status_options, command=self.change_status)
        
        status_menu.grid(row=2, column=1, padx=10, pady=10)
        status_menu_label = tk.Label(web_design_widgets["input_frame"], text="status:", bg='#CCD5AE')
        status_menu_label.grid(row=2, column=0, padx=10, pady=10)
        status_menu.config(style='Custom.TMenubutton')
        industry_options = ["tech", "creative", "finance", "healthcare", "education", "legal", "manufacturing", "public_service", "other"]
        self.industry_var = tk.StringVar(value="tech")
        industry_menu = ttk.OptionMenu(web_design_widgets["input_frame"], self.industry_var, industry_options[0], *industry_options, command=self.on_industry_change)
        industry_menu.config(style='Custom.TMenubutton')
        industry_menu.grid(row=3, column=1, padx=10, pady=10)
        industry_menu_label = tk.Label(web_design_widgets["input_frame"], text="industry:", bg='#CCD5AE')
        industry_menu_label.grid(row=3, column=0, padx=10, pady=10)

        input_labels = ["save_file", "basic_information", "academic_achievements", "experience", "professional_skills", "website_template_path", "feedback", "each refine times", "local_img_storage_path"]
        for i in range(4, 13):
            label = tk.Label(web_design_widgets['input_frame'], text=input_labels[i - 4], bg='#CCD5AE')
            entry = tk.Entry(web_design_widgets['input_frame'])
            label.grid(row=i, column=0, padx=10, pady=5)
            entry.grid(row=i, column=1, padx=10, pady=5)
            if i != 12:
                clear_button = tk.Button(web_design_widgets['input_frame'], text="Clear", command=lambda e=entry: e.delete(0, tk.END), bg='#FEFAE0')
                clear_button.grid(row=i, column=2, padx=10, pady=5)
            web_design_widgets["input_labels"].append(label)
            web_design_widgets["input_entries"].append(entry)

        local_img_storage_button = tk.Button(web_design_widgets['input_frame'], text="load", command=self.upload_local_img_storage, bg='#FEFAE0')
        local_img_storage_button.grid(row=12, column=2, padx=10, pady=10)

        gen_img_options = ["Gen", "Local", "None"]
        gen_img_var = tk.StringVar(value="Gen")
        self.gen_img_var = gen_img_var
        gen_img_menu = ttk.OptionMenu(web_design_widgets["input_frame"], gen_img_var, gen_img_options[0], *gen_img_options, command=self.change_gen_img)
        gen_img_menu.config(style='Custom.TMenubutton')
        gen_img_menu.grid(row=13, column=1, padx=10, pady=10)
        gen_img_menu_label = tk.Label(web_design_widgets["input_frame"], text="IMG Source:", bg='#CCD5AE')
        gen_img_menu_label.grid(row=13, column=0, padx=10, pady=10)
        self.gen_img_menu = gen_img_menu
        self.agent.gen_img = gen_img_options[0]


        label = tk.Label(web_design_widgets["input_frame"], text="🤖 Status: ", bg='#CCD5AE')
        label.grid(row=14, column=0, padx=10, pady=10)
        self.animation_label = tk.Label(web_design_widgets["input_frame"], text="💡 idle", bg='#CCD5AE')
        self.animation_label.grid(row=14, column=1, columnspan=2, padx=10, pady=10)
        self.animation_idx = 0


        label = tk.Label(web_design_widgets["input_frame"], text="💰 Total Token Cost: ", bg='#CCD5AE')
        label.grid(row=15, column=0, padx=10, pady=10)
        self.token_cost_label = tk.Label(web_design_widgets["input_frame"], wraplength=200, text="💰 0 $", bg='#CCD5AE')
        self.token_cost_label.grid(row=15, column=1, columnspan=2, padx=10, pady=10)

        label = tk.Label(web_design_widgets["input_frame"], text="💰 Total IMG Cost: ", bg='#CCD5AE')
        label.grid(row=16, column=0, padx=10, pady=10)
        self.token_img_label = tk.Label(web_design_widgets["input_frame"], wraplength=200, text="💰 0 $", bg='#CCD5AE')
        self.token_img_label.grid(row=16, column=1, columnspan=2, padx=10, pady=10)


        label = tk.Label(web_design_widgets["input_frame"], text="⏱️ Time Cost: ", bg='#CCD5AE')
        label.grid(row=17, column=0, padx=10, pady=10)
        self.time_label = tk.Label(web_design_widgets["input_frame"], wraplength=200, text="⏱️ 0 s", bg='#CCD5AE')
        self.time_label.grid(row=17, column=1, columnspan=2, padx=10, pady=10)

        plan_button = tk.Button(self.scrollable_frame, text="Plan", command=self.plan, bg='#FEFAE0')
        auto_gen_button = tk.Button(self.scrollable_frame, text="Auto Generate", command=self.auto_gen_website, bg='#FEFAE0')
        clean_useless_imgs_button = tk.Button(self.scrollable_frame, text="Clean Useless IMG", command=self.clean, bg='#FEFAE0')
        cancel_button = tk.Button(self.scrollable_frame, text="cancel", command=self.cancel, bg='#FEFAE0')

        restore_backup_html_button = tk.Button(self.scrollable_frame, text="backup", command=self.restore_backup_html, bg="black", fg='white')
        create_button = tk.Button(self.scrollable_frame, text="Create Website", command=self.create_website, bg='#FEFAE0')
        refine_button = tk.Button(self.scrollable_frame, text="Refine Website", command=self.refine_website, bg='#FEFAE0')
        open_website_button = tk.Button(self.scrollable_frame, text="Open Website", command=self.open_website, bg='#FEFAE0')

        delete_page_button = tk.Button(self.scrollable_frame, text="Delete Page", command=self.delete_page, bg='#FEFAE0')
        add_page_button = tk.Button(self.scrollable_frame, text="Add Page", command=self.add_page, bg='#FEFAE0')
        complete_page_button = tk.Button(self.scrollable_frame, text="Complete Page", command=self.complete_page, bg='#FEFAE0')
        refine_page_button = tk.Button(self.scrollable_frame, text="Refine Page", command=self.refine_page, bg='#FEFAE0')

        web_design_widgets["plan_button"] = plan_button
        web_design_widgets["auto_gen_button"] = auto_gen_button
        web_design_widgets["clean_useless_imgs_button"] = clean_useless_imgs_button
        web_design_widgets['cancel'] = cancel_button

        web_design_widgets["restore_backup_html_button"] = restore_backup_html_button
        web_design_widgets["create_button"] = create_button
        web_design_widgets["refine_button"] = refine_button
        web_design_widgets["open_website_button"] = open_website_button

        web_design_widgets["delete_page_button"] = delete_page_button
        web_design_widgets["add_page_button"] = add_page_button
        web_design_widgets["complete_page_button"] = complete_page_button
        web_design_widgets["refine_page_button"] = refine_page_button

        return web_design_widgets

    def cancel(self):
        self.is_animating = False
    
    def on_css_frame_change(self, css_frame):
        if css_frame == "None":
            self.agent.css_frame = None
        else:
            self.agent.css_frame = css_frame
        print(f"Change CSS Frame to: {css_frame}")

    def switch_model(self,model):
        self.agent.model = model
        print(f"Switched to {model}")

    def upload_local_img_storage(self):
        if self.agent.vision == False:
            messagebox.showerror("Error", "Please open the vision first")
            return
        self.read_input_entries()
        self.is_animating = True
        threading.Thread(target=self.animate, args=(["🤔💭 Uploading now", "🧐💭 Uploading now.", "😅💭 Uploading now..", "🤯💭 Uploading now..."],)).start()
        def long_operation():
            try:
                self.agent.load_local_img_storage()
                self.is_animating = False
                self.update_cost()
            except Exception as e:
                messagebox.showerror("Error", f"Error occurred: {e}")
                self.is_animating = False
        self.begin_time = time.time()
        threading.Thread(target=long_operation).start()
        print(f"Upload local_img_storage to: {self.agent.local_img_storage_path}")

    def change_gen_img(self,gen_img):
        if gen_img == "None":
            self.agent.gen_img = False
            self.agent.local_img_storage_copy = self.agent.local_img_storage.copy()
            self.agent.local_img_storage = []
        elif gen_img == "Local":
            if not self.agent.local_img_storage:
                messagebox.showerror("Please upload the local_img_storage, current is empty")
            self.agent.gen_img = gen_img
            if self.agent.local_img_storage_copy:
                self.agent.local_img_storage = self.agent.local_img_storage_copy.copy()
            print(self.agent.local_img_storage)
        else:
            self.agent.gen_img = gen_img
            self.agent.local_img_storage_copy = self.agent.local_img_storage.copy()
            self.agent.local_img_storage = []
        print(f"Change Gen IMG to: {gen_img}")

    def change_language(self,language):
        self.agent.language = language
        print(f"Change language to: {language}")

    def change_status(self,status):
        self.agent.status = status
        print(f"Change your status: {status}")

    def on_industry_change(self,industry):
        self.agent.industry = industry
        print(f"Change industry to: {industry}")
    
    def clear_widgets(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.grid_forget()

    def display_web_design_mode(self):
        self.web_design_widgets['input_frame'].grid(row=1, column=0, padx=10, pady=10)
        self.web_design_widgets['plan_button'].grid(row=2, column=0, padx=10, pady=10)
        self.web_design_widgets['auto_gen_button'].grid(row=3, column=0, padx=10, pady=10)
        self.web_design_widgets['clean_useless_imgs_button'].grid(row=4, column=0, padx=10, pady=10)
        self.web_design_widgets['cancel'].grid(row=5, column=0, padx=10, pady=10)

        self.web_design_widgets['output_text'].grid(row=1, column=1, padx=10, pady=10)
        self.web_design_widgets['delete_page_button'].grid(row=2, column=1, padx=10, pady=10)
        self.web_design_widgets['add_page_button'].grid(row=3, column=1, padx=10, pady=10)
        self.web_design_widgets['complete_page_button'].grid(row=4, column=1, padx=10, pady=10)
        self.web_design_widgets['refine_page_button'].grid(row=5, column=1, padx=10, pady=10)

        self.web_design_widgets['output_image_frame'].grid(row=1, column=2, padx=10, pady=10)
        self.web_design_widgets['restore_backup_html_button'].grid(row=2, column=2, padx=10, pady=10)
        self.web_design_widgets['create_button'].grid(row=3, column=2, padx=10, pady=10)
        self.web_design_widgets['refine_button'].grid(row=4, column=2, padx=10, pady=10)
        self.web_design_widgets['open_website_button'].grid(row=5, column=2, padx=10, pady=10)

    def read_input_entries(self):
        input_entries = self.web_design_widgets["input_entries"]
        save_file = input_entries[0].get()
        self.agent.change_save_file(save_file)
        self.agent.task["basic_information"] = input_entries[1].get()
        self.agent.task["academic achievements"] = input_entries[2].get()
        self.agent.task["experience"] = input_entries[3].get()
        self.agent.task["professional_skills"] = input_entries[4].get()
        self.agent.task["img"] = input_entries[5].get() if self.agent.vision else None
        self.agent.user_feedback = input_entries[6].get() if input_entries[6].get() else ""
        self.agent.refine_times = int(input_entries[7].get()) if input_entries[7].get() else 2
        self.agent.local_img_storage_path = self.web_design_widgets["input_entries"][8].get() if self.web_design_widgets["input_entries"][5].get() else ""
    

    def plan(self):
        if self.is_animating:
            messagebox.showerror("Error", "Please wait for the current operation to finish")
            return
        def long_operation():
            try:
                self.pages = self.agent.plan()
                self.is_animating = False
                self.current_page = 0
                self.display_table_page()
                self.update_cost()
            except Exception as e:
                messagebox.showerror("Error", f"Error occurred: {e}")
                self.is_animating = False

        for widget in self.web_design_widgets['output_image_frame'].winfo_children():
            widget.destroy()
        for widget in self.web_design_widgets['output_text'].winfo_children():
            widget.destroy()

        if not self.agent:
            messagebox.showerror("Error", "Please initialize the agent first")
            return
        self.read_input_entries()
        basic_information = self.web_design_widgets["input_entries"][1].get()
        academic_achievements = self.web_design_widgets["input_entries"][2].get()
        experience = self.web_design_widgets["input_entries"][3].get()
        professional_skills = self.web_design_widgets["input_entries"][4].get()
        website_img = self.web_design_widgets["input_entries"][5].get() if self.agent.vision else None
        feedback = self.web_design_widgets["input_entries"][6].get()
        if not (basic_information or academic_achievements or experience or professional_skills) and not os.path.exists(website_img):
            try:
                self.agent.driver.get_screenshot(website_img,"target_website.png",False)
            except:
                messagebox.showerror("Error", "Please upload the website image or input the website description")
                return

        self.agent.publish_task(img=website_img, basic_information=basic_information, academic_achievements=academic_achievements, experience=experience, professional_skills=professional_skills, feedback=feedback)

        animation_sequence = ["🤔💭 Planning now", "🧐💭 Planning now.", "😅💭 Planning now..", "🤯💭 Planning now..."]
        self.is_animating = True
        self.begin_time = time.time()
        threading.Thread(target=self.animate, args=(animation_sequence,)).start()
        threading.Thread(target=long_operation).start()

    def display_table_page(self):
        table_frame = self.web_design_widgets["output_text"]
        for widget in table_frame.winfo_children():
            widget.destroy()
        
        table_frame.config(state='disabled', wrap=tk.WORD, width=50, height=50)
        if self.pages:
            item = self.pages[self.current_page]
            cnt = 0
            for i, (key, value) in enumerate(item.items()):
                tk.Label(table_frame, text=key, bg='#F5EFE6').grid(row=i, column=0, sticky='e')
                text_frame = tk.Frame(table_frame)
                text_frame.grid(row=i, column=1, sticky='w')
                if key in ["is_main_page","html_name","css_name"]:  
                    text_widget = tk.Text(text_frame, wrap=tk.WORD, height=1, width=35)
                elif key == "relationship":
                    text_widget = tk.Text(text_frame, wrap=tk.WORD, height=15, width=35)
                else:
                    text_widget = tk.Text(text_frame, wrap=tk.WORD, height=5, width=35)
                text_widget.insert(tk.END, value)
                text_widget.pack(side=tk.LEFT, expand=True, fill='both')
                scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview, bg='#A6B37D')
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                text_widget.config(yscrollcommand=scrollbar.set)
                text_widget.bind("<FocusOut>", lambda e, k=key, idx=self.current_page: self.save_value(e, k, idx))
                cnt = i
            
            canvas = tk.Canvas(table_frame, width=500, height=80, bg='#A6B37D')
            canvas.grid(row=cnt+1, column=0, columnspan=2)
            scrollbar = tk.Scrollbar(table_frame, command=canvas.yview, bg='#A6B37D')
            scrollbar.grid(row=cnt+1, column=2, sticky='ns')
            canvas.config(yscrollcommand=scrollbar.set)
            self.inner_frame = tk.Frame(canvas, bg='#A6B37D')
            self.inner_frame_id = canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')
            self.create_blocks(self.inner_frame)
            self.inner_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"), bg='#A6B37D')

            self.block_canvas = canvas
            self.inner_frame.bind('<Configure>', self.on_frame_resize)

            html_name = item["html_name"]
            html_path = os.path.join(self.agent.save_file, html_name)
            page_name = html_name.split(".")[0]
            page_img_path = os.path.join(self.agent.save_file, f"{page_name}.png")
            if html_name and os.path.exists(html_path):
                if not os.path.exists(page_img_path):
                    self.agent.webserver.get_screenshot(html_path, page_img_path)
                self.update_ui_after_refine_website()


        table_frame.grid(row=1, column=1, padx=10, pady=10)


    def create_blocks(self, frame):
        self.buttons = []
        block_width = 5
        blocks_per_row =  6
        page_list = self.pages
        for idx, value in enumerate(page_list):
            html_name = value["html_name"]
            html_path = os.path.join(self.agent.save_file, html_name)
            color = "#365E32" if os.path.exists(html_path) else "gray"
            row = idx // blocks_per_row
            col = idx % blocks_per_row
            page_name = html_name.split(".")[0]
            button = tk.Button(frame, text=page_name, bg=color, width=block_width, height=2,
                               command=lambda idx=idx: self.on_block_click(idx),font=("Arial", 10))

            button.grid(row=row, column=col, padx=5, pady=5)
            self.buttons.append(button)



    def on_frame_resize(self, event):
        canvas_width = event.width
        self.nametowidget(self.block_canvas).itemconfig(self.inner_frame_id, width=canvas_width)

        self.nametowidget(self.block_canvas).config(scrollregion=self.nametowidget(self.block_canvas).bbox("all"))


    def on_block_click(self, idx):
        self.current_page = idx
        self.display_table_page()


    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.display_table_page()
    
    def next_page(self):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.display_table_page()

    def delete_page(self):
        if self.pages:
            current_page = self.pages[self.current_page]
            html_name = current_page["html_name"]
            for i,page in enumerate(self.pages):
                if isinstance(page["relationship"], dict):
                    for j,button in enumerate(page["relationship"]["buttons"]):
                        if "jump_page" in button and button["jump_page"] == html_name:
                            self.pages[i]["relationship"]["buttons"].pop(j)
                    for j,link in enumerate(page["relationship"]["links"]):
                        if "jump_page" in link and link["jump_page"] == html_name:
                            self.pages[i]["relationship"]["links"].pop(j)
            self.pages.pop(self.current_page)
            if self.current_page >= len(self.pages):
                self.current_page = len(self.pages) - 1
            self.display_table_page()

    def refine_page(self):
        self.read_input_entries()
        if self.is_animating:   
            messagebox.showerror("Error", "Please wait for the current operation to finish")
            return
        if self.pages:
            animation_sequence = ["🤔💭 Refine now", "🧐💭 Refine now.", "😅💭 Refine now..", "🤯💭 Refine now..."]
            self.is_animating = True
            threading.Thread(target=self.animate, args=(animation_sequence,)).start()
            def long_operation():
                try:
                    page = self.pages[self.current_page]
                    html_name = page["html_name"]
                    html_path = os.path.join(self.agent.save_file, html_name)
                    if not os.path.exists(html_path):
                        messagebox.showerror("Error", "Please create the website first")
                        return
                    feedback = self.web_design_widgets["input_entries"][6].get()
                    self.pages[self.current_page] = self.agent.refine_page(page,feedback)
                    with open(os.path.join(self.agent.save_file, "pages.json"), "w",encoding='utf-8') as f:
                        json.dump(self.pages, f)
                    self.is_animating = False
                    self.display_table_page()
                    self.update_cost()
                except Exception as e:
                    messagebox.showerror("Error", f"Error occurred: {e}")
                    self.is_animating = False
            self.begin_time = time.time()
            threading.Thread(target=long_operation).start()
    
    def restore_backup_html(self):
        if self.is_animating:   
            messagebox.showerror("Error", "Please wait for the current operation to finish")
            return
        page = self.pages[self.current_page]
        html_name = page["html_name"]
        page_name = html_name.split(".")[0]
        current_path = os.path.join(self.agent.save_file, html_name)
        current_img_path = os.path.join(self.agent.save_file,f"{page_name}.png")
        backup_folder_path = self.create_backup_folder(self.agent.save_file)
        backup_html = os.path.join(backup_folder_path, f"backup_{html_name}")
        backup_img = os.path.join(backup_folder_path, f"backup_{page_name}.png")
        if os.path.exists(backup_folder_path):
            shutil.copy(backup_html, current_path)
            shutil.copy(backup_img, current_img_path)
            print(f"已恢复到上一次生成的 HTML 文件: {backup_folder_path}")
            messagebox.showinfo("恢复成功", f"已恢复到上一次生成的文件: {page_name}")
        else:
            print(f"备份文件 {backup_folder_path} 不存在，无法恢复。")
            messagebox.showerror("恢复失败", f"备份文件 {backup_folder_path} 不存在，无法恢复。")

    def complete_page(self):
        self.read_input_entries()
        if self.is_animating:
            messagebox.showerror("Error", "Please wait for the current operation to finish")
            return
        self.is_animating = True

        animation_sequence = ["🤔💭 Completing now", "🧐💭 Completing now.", "😅💭 Completing now..", "🤯💭 Completing now..."]
        threading.Thread(target=self.animate, args=(animation_sequence,)).start()
        def long_operation():
            try:
                self.pages = self.agent.complete_page(self.pages, self.current_page)
                with open(os.path.join(self.agent.save_file, "pages.json"), "w",encoding='utf-8') as f:
                    json.dump(self.pages, f)
                self.is_animating = False
                self.display_table_page()
                self.update_cost()
            except Exception as e:
                messagebox.showerror("Error", f"Error occurred: {e}")
                self.is_animating = False
        self.begin_time = time.time()
        threading.Thread(target=long_operation).start()

    def add_page(self):
        page_template = {}
        for key in self.pages[0].keys():
            page_template[key] = ""
        self.pages.append(page_template)
        self.current_page = len(self.pages) - 1
        self.display_table_page()


    def save_backup(self, current_path, backup_path):
        if os.path.exists(current_path):
            shutil.copy(current_path, backup_path)
            print(f"备份已保存: {backup_path}")
        else:
            print(f"当前文件 {current_path} 不存在，无法备份。")
    
    def open_website(self):
        html_name = self.pages[self.current_page]["html_name"]
        html_path = os.path.join(self.agent.save_file, html_name)
        self.agent.webserver.open_website(html_path)
        

    def save_value(self, event, key, idx):
        text_widget = event.widget
        text_widget.config(state=tk.NORMAL)
        value = text_widget.get("1.0", tk.END).strip()
        text_widget.config(state=tk.DISABLED)
        self.pages[idx][key] = value
        save_file = self.web_design_widgets["input_entries"][0].get()
        pages_path = os.path.join(save_file, "pages.json")
        with open(pages_path, "w",encoding='utf-8') as f:
            json.dump(self.pages, f)
    
    def update_cost(self):
        with open("logs/token.json", "r") as f:
            tokens = json.load(f)
        llm_name = self.agent.model
        current_prompt_cost = tokens[llm_name][0]
        current_completion_cost = tokens[llm_name][1]
        total_prompt_cost = current_prompt_cost - self.begin_cost[llm_name][0]
        total_completion_cost = current_completion_cost - self.begin_cost[llm_name][1]  
        self.total_cost = cal_cost(total_prompt_cost, total_completion_cost,self.agent.model)
        self.time_cost += time.time() - self.begin_time
        self.token_cost_label.config(text=f"💰 {self.total_cost} $")
        self.time_label.config(text=f"⏱️ {self.time_cost} s")
    
    def create_website(self):
        animation_sequence = ["🤔💭 Creating now", "🧐💭 Creating now.", "😅💭 Creating now..", "🤯💭 Creating now..."]
        if self.is_animating:
            messagebox.showerror("Error", "Please wait for the current operation to finish")
            return
        self.read_input_entries()

        self.is_animating = True
        threading.Thread(target=self.animate, args=(animation_sequence,)).start()
        def long_operation():
            try:
                if not self.pages:
                    messagebox.showerror("Error", "Please plan the website first")
                    return
                page = self.pages[self.current_page]

                html_name = page["html_name"]
                page_name = html_name.split(".")[0]
                html_path = os.path.join(self.agent.save_file, html_name)
                img_path = os.path.join(self.agent.save_file,f"{page_name}.png")
                backup_folder_path = self.create_backup_folder(self.agent.save_file)
                print(img_path, backup_folder_path, page_name)
                if page:
                    backup_html = os.path.join(backup_folder_path, f"backup_{html_name}")
                    backup_img = os.path.join(backup_folder_path, f"backup_{page_name}.png")
                    print(backup_html, backup_img)
                    self.save_backup(current_path=html_path, backup_path=backup_html)
                    self.save_backup(current_path=img_path, backup_path=backup_img)
                self.agent.write_original_website(page)
                self.after(0, self.update_ui_after_refine_website)
                self.is_animating = False
                self.update_cost()
            except Exception as e:
                messagebox.showerror("Error", f"Error occurred: {e}")
                self.is_animating = False

        self.begin_time = time.time()
        threading.Thread(target=long_operation).start()
    
    def refine_website(self):
        if self.is_animating:
            messagebox.showerror("Error", "Please wait for the current operation to finish")
            return
        animation_sequence = ["🤔💭 Refine now", "🧐💭 Refine now.", "😅💭 Refine now..", "🤯💭 Refine now..."]
        self.is_animating = True
        threading.Thread(target=self.animate, args=(animation_sequence,)).start()
        self.read_input_entries()

        def long_operation():
            try:
                self.agent.user_feedback = self.web_design_widgets["input_entries"][6].get()
                page = self.pages[self.current_page]

                html_name = page["html_name"]
                page_name = html_name.split(".")[0]
                html_path = os.path.join(self.agent.save_file, html_name)
                img_path = os.path.join(self.agent.save_file,f"{page_name}.png")
                backup_folder_path = self.create_backup_folder(self.agent.save_file)
                if not os.path.exists(html_path):
                    messagebox.showerror("Error", "Please create the website first")
                    return
                if page:
                    backup_html = os.path.join(backup_folder_path, f"backup_{html_name}")
                    backup_img = os.path.join(backup_folder_path, f"backup_{page_name}.png")
                    self.save_backup(current_path=html_path, backup_path=backup_html)
                    self.save_backup(current_path=img_path, backup_path=backup_img)
                self.agent.refine(page)            
                self.after(0, self.update_ui_after_refine_website)
                self.is_animating = False
                self.update_cost()
            except Exception as e:
                messagebox.showerror("Error", f"Error occurred: {e}")
                self.is_animating = False
        self.begin_time = time.time()
        threading.Thread(target=long_operation).start()

    def update_ui_after_refine_website(self):
        page = self.pages[self.current_page]
        html_name = page["html_name"]
        for widget in self.web_design_widgets['output_image_frame'].winfo_children():
            widget.destroy()

        if os.path.exists(os.path.join(self.agent.save_file, html_name)):
            page_name = html_name.split(".")[0]
            page_img_path = os.path.join(self.agent.save_file, f"{page_name}.png")
            img = Image.open(page_img_path)
            if img.size[0] > 600:
                width,height = img.size
                img = img.resize((600, int(600/width*height)))
            img = ImageTk.PhotoImage(img)   
            canvas = tk.Canvas(self.web_design_widgets['output_image_frame'], width=600, height=600, bg='#CCD5AE')
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            v_scrollbar = tk.Scrollbar(self.web_design_widgets['output_image_frame'], orient=tk.VERTICAL, command=canvas.yview, bg='#A6B37D')
            x_scrollbar = tk.Scrollbar(self.web_design_widgets['output_image_frame'], orient=tk.HORIZONTAL, command=canvas.xview, bg='#A6B37D')
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            canvas.configure(yscrollcommand=v_scrollbar.set, bg='#CCD5AE')
            canvas.configure(xscrollcommand=x_scrollbar.set, bg='#CCD5AE')
            image_frame = tk.Frame(canvas, bg='#CCD5AE')
            canvas.create_window((0, 0), window=image_frame, anchor="nw")
            img_label = tk.Label(image_frame, image=img, bg='#CCD5AE')
            img_label.image = img
            img_label.pack()
            image_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"), bg='#CCD5AE')

            def on_frame_resize(event):
                canvas.config(scrollregion=canvas.bbox("all"))

            image_frame.bind("<Configure>", on_frame_resize)            
            self.img_ref = img

    def auto_gen_website(self):
        if self.is_animating:
            messagebox.showerror("Error", "Please wait for the current operation to finish")
            return
        self.is_animating = True
        animation_sequence = ["🤔💭 Generating now", "🧐💭 Generating now.", "😅💭 Generating now..", "🤯💭 Generating now..."]
        self.read_input_entries()
        
        threading.Thread(target=self.animate, args=(animation_sequence,)).start()
        def long_operation():
            try:
                self.begin_time = time.time()
                
                if not self.pages:
                    self.pages = self.agent.plan()
                self.update_cost()
                need_create_pages = []
                for page in self.pages:
                    html_name = page["html_name"]
                    html_path = os.path.join(self.agent.save_file, html_name)

                    if not os.path.exists(html_path) and page["description"]:
                        need_create_pages.append(page)
            except Exception as e:
                messagebox.showerror("Error", f"Error occurred: {e}")
                self.is_animating = False
                return
            
            asyncio.run(self.agent.deal_task_async(need_create_pages))
            self.update_cost()
            self.is_animating = False
        threading.Thread(target=long_operation).start()

    def clean(self):
        self.agent.clean()
    
    def create_backup_folder(self, save_file):
        backup_folder = os.path.join(save_file, "backup")
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
            print(f"Backup 文件夹已创建: {backup_folder}")
        else:
            print(f"Backup 文件夹已存在: {backup_folder}")
        return backup_folder

    def animate(self,animation_sequence):
        if self.is_animating:
            self.animation_label.config(text=animation_sequence[self.animation_idx])
            self.animation_idx = (self.animation_idx + 1) % len(animation_sequence)
            self.after(300, lambda: self.animate(animation_sequence))
        else:
            self.animation_label.config(text="💡 idle")


if __name__ == "__main__":
    agent = HomepageDesignAgent()
    app = Application(agent=agent)
    app.mainloop()


