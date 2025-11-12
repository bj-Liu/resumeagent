import sys
sys.path.append("..") 
import openai
import retry
import requests
from vl_prompt.p_manager import extract_integer_answer, extract_scores, extract_objects, \
    get_frontier_prompt, get_candidate_prompt, get_grouping_prompt, get_discover_prompt, get_decisionTiming_prompt, extract_interval_steps

from openai import AzureOpenAI

import os


class LLM():
    def __init__(self, goal_name, prompt_type):         
        self.goal_name = goal_name
        self.prompt_type = prompt_type
        self.history = []
        self.max_tokens = 2000
        self.headers = {                             
        "Content-Type": "application/json",
        "api-key": GPT4V_KEY,
    }

    
    def inference_once(self, system_prompt, message):
        if message:
            msg = {
                "role": "user",
                "content": message
            }
            self.history = system_prompt + [msg]
            try:
                payload = {'messages': self.history}
                response = requests.post(GPT4V_ENDPOINT, headers=self.headers, json=payload)
                response.raise_for_status() 
                reply = response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"=====> llm inference error: {e}")
                
        return reply                                      
    

    def discover_objects(self, img, objects):
        payload = get_discover_prompt(img, objects)
        response = requests.post(GPT4V_ENDPOINT, headers=self.headers, json=payload)
        reply = response.json()["choices"][0]["message"]["content"]
        c = extract_objects(reply)
        return c
    
    def choose_decision_step(self, img):
        payload = get_decisionTiming_prompt(img)
        response = requests.post(GPT4V_ENDPOINT, headers=self.headers, json=payload)
        reply = response.json()["choices"][0]["message"]["content"]
        c = extract_interval_steps(reply)
        return c   
    
    def inference_accumulate(self, message):
        if message:
            self.history.append(
                {"role": "user", "content": message},
            )
            try:
                payload = {'messages': self.history}
                response = requests.post(GPT4V_ENDPOINT, headers=self.headers, json=payload)
                response.raise_for_status() 
                reply = response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"=====> llm inference error: {e}")

        self.history.append({"role": "assistant", "content": reply})
        return reply
    

    def choose_frontier(self, message):
        system_prompt = get_frontier_prompt(self.prompt_type)
        reply = self.inference_once(system_prompt, message)
        if self.prompt_type == "deterministic":
            answer = extract_integer_answer(reply)
        elif self.prompt_type == "scoring":
            answer, scores = extract_scores(reply)
        
        return answer, reply
        
    def imagine_candidate(self, instr):
        system_prompt = get_candidate_prompt(candidate_type="open")
        reply = self.inference_once(system_prompt, instr)
        c = extract_objects(reply)
        return c
    
    def group_candidate(self, clist, nlist):
        system_prompt = get_grouping_prompt()
        message = f"Current object list: {clist}\n\nNew object list: {nlist}"
        reply = self.inference_once(system_prompt, message)
        c = extract_objects(reply) 
        new_c = []
        for ob in c:
            if ("room" in ob) or ("wall" in ob) or ("floor" in ob) or ("ceiling" in ob):
                continue
            new_c.append(ob)
        return new_c