from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.spinner import Spinner
from kivy.core.clipboard import Clipboard
import requests
import json
import threading

# Definir tamanho da janela
Window.size = (800, 600)

class LoadingPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Carregando...'
        self.size_hint = (0.3, 0.2)
        self.auto_dismiss = False
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.progress = ProgressBar(max=100, value=0)
        content.add_widget(self.progress)
        self.add_widget(content)
    
    def update_progress(self, dt):
        if self.progress.value < 100:
            self.progress.value += 1
        else:
            self.progress.value = 0

class BaseScreen(Screen):
    def show_loading(self, dt=None):
        self.loading_popup = LoadingPopup()
        self.loading_popup.open()
        Clock.schedule_interval(self.loading_popup.update_progress, 0.01)
    
    def hide_loading(self, dt=None):
        if hasattr(self, 'loading_popup'):
            Clock.unschedule(self.loading_popup.update_progress)
            self.loading_popup.dismiss()

class MenuScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        title = Label(
            text='Todo API Interface',
            size_hint_y=None,
            height=100,
            font_size=32
        )
        layout.add_widget(title)
        
        buttons_layout = BoxLayout(orientation='vertical', spacing=10)
        
        create_btn = Button(
            text='Criar Nova Tarefa',
            size_hint_y=None,
            height=60,
            background_color=(0.2, 0.6, 0.9, 1)
        )
        create_btn.bind(on_press=self.go_to_create)
        
        list_btn = Button(
            text='Listar Tarefas',
            size_hint_y=None,
            height=60,
            background_color=(0.2, 0.8, 0.2, 1)
        )
        list_btn.bind(on_press=self.go_to_list)
        
        update_btn = Button(
            text='Atualizar Tarefa',
            size_hint_y=None,
            height=60,
            background_color=(0.9, 0.6, 0.2, 1)
        )
        update_btn.bind(on_press=self.go_to_update)
        
        delete_btn = Button(
            text='Deletar Tarefa',
            size_hint_y=None,
            height=60,
            background_color=(0.9, 0.2, 0.2, 1)
        )
        delete_btn.bind(on_press=self.go_to_delete)
        
        buttons_layout.add_widget(create_btn)
        buttons_layout.add_widget(list_btn)
        buttons_layout.add_widget(update_btn)
        buttons_layout.add_widget(delete_btn)
        
        layout.add_widget(buttons_layout)
        self.add_widget(layout)

    def go_to_create(self, instance):
        self.manager.current = 'create'
        
    def go_to_list(self, instance):
        self.manager.current = 'list'
        
    def go_to_update(self, instance):
        self.manager.current = 'update'
        
    def go_to_delete(self, instance):
        self.manager.current = 'delete'

class CreateScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        title = Label(
            text='Criar Nova Tarefa',
            size_hint_y=None,
            height=50,
            font_size=24
        )
        layout.add_widget(title)
        
        form = GridLayout(cols=2, spacing=10, size_hint_y=None, height=200)
        
        form.add_widget(Label(text='Título:'))
        self.title_input = TextInput(multiline=False)
        form.add_widget(self.title_input)
        
        form.add_widget(Label(text='Descrição:'))
        self.description_input = TextInput(multiline=True)
        form.add_widget(self.description_input)
        
        form.add_widget(Label(text='Status:'))
        self.status_input = Spinner(
            text='Selecione um status',
            values=('pendente', 'concluido', 'em andamento'),
            size_hint_y=None,
            height=40
        )
        form.add_widget(self.status_input)
        
        layout.add_widget(form)
        
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        back_btn = Button(
            text='Voltar ao Menu',
            background_color=(0.7, 0.7, 0.7, 1)
        )
        back_btn.bind(on_press=self.go_to_menu)
        
        create_btn = Button(
            text='Criar Tarefa',
            background_color=(0.2, 0.6, 0.9, 1)
        )
        create_btn.bind(on_press=self.create_task)
        
        button_layout.add_widget(back_btn)
        button_layout.add_widget(create_btn)
        
        layout.add_widget(button_layout)
        self.add_widget(layout)
    
    def go_to_menu(self, instance):
        self.manager.current = 'menu'
    
    def create_task(self, instance):
        def create_task_thread():
            try:
                Clock.schedule_once(self.show_loading)
                data = {
                    'title': self.title_input.text,
                    'description': self.description_input.text,
                    'status': self.status_input.text
                }
                response = requests.post('http://localhost:8000/tasks/', json=data)
                if response.status_code == 200:
                    def on_success(dt):
                        self.clear_form()
                        self.manager.get_screen('list').refresh_tasks()
                        self.manager.current = 'list'
                    Clock.schedule_once(on_success)
            except Exception as e:
                print(f"Erro ao criar tarefa: {e}")
            finally:
                Clock.schedule_once(self.hide_loading)
        
        threading.Thread(target=create_task_thread).start()
    
    def clear_form(self):
        self.title_input.text = ''
        self.description_input.text = ''
        self.status_input.text = ''

class ListScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tasks = []  # Lista para armazenar as tarefas
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Botões de navegação
        nav_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        nav_layout.add_widget(Button(text='Criar Tarefa', on_press=self.switch_to_create))
        nav_layout.add_widget(Button(text='Atualizar Tarefa', on_press=self.switch_to_update))
        nav_layout.add_widget(Button(text='Deletar Tarefa', on_press=self.switch_to_delete))
        layout.add_widget(nav_layout)
        
        # Tabela de tarefas
        self.table = GridLayout(cols=5, spacing=5, size_hint_y=None)
        self.table.bind(minimum_height=self.table.setter('height'))
        
        # Cabeçalhos
        self.table.add_widget(Label(text='ID', size_hint_y=None, height=40))
        self.table.add_widget(Label(text='Título', size_hint_y=None, height=40))
        self.table.add_widget(Label(text='Descrição', size_hint_y=None, height=40))
        self.table.add_widget(Label(text='Status', size_hint_y=None, height=40))
        self.table.add_widget(Label(text='Ações', size_hint_y=None, height=40))
        
        # ScrollView para a tabela
        scroll = ScrollView()
        scroll.add_widget(self.table)
        layout.add_widget(scroll)
        
        # Indicador de carregamento
        self.loading_label = Label(text='Carregando...', size_hint_y=None, height=30)
        layout.add_widget(self.loading_label)
        
        self.add_widget(layout)
        self.refresh_tasks()

    def switch_to_create(self, instance):
        self.manager.current = 'create'

    def switch_to_update(self, instance):
        self.manager.current = 'update'

    def switch_to_delete(self, instance):
        self.manager.current = 'delete'

    def update_table(self, tasks):
        # Limpar a tabela, mantendo os cabeçalhos
        self.table.clear_widgets()
        
        # Adicionar cabeçalhos novamente
        self.table.add_widget(Label(text='ID', size_hint_y=None, height=40))
        self.table.add_widget(Label(text='Título', size_hint_y=None, height=40))
        self.table.add_widget(Label(text='Descrição', size_hint_y=None, height=40))
        self.table.add_widget(Label(text='Status', size_hint_y=None, height=40))
        self.table.add_widget(Label(text='Ações', size_hint_y=None, height=40))
        
        # Adicionar tarefas
        for task in tasks:
            self.table.add_widget(Label(text=str(task['id']), size_hint_y=None, height=40))
            self.table.add_widget(Label(text=task['title'], size_hint_y=None, height=40))
            self.table.add_widget(Label(text=task['description'], size_hint_y=None, height=40))
            self.table.add_widget(Label(text=task['status'], size_hint_y=None, height=40))
            
            # Botão para copiar ID
            copy_btn = Button(
                text='Copiar ID',
                size_hint_y=None,
                height=40,
                background_color=(0.2, 0.8, 0.2, 1)  # Verde
            )
            copy_btn.bind(on_press=lambda btn, id=task['id']: self.copy_task_id(id))
            self.table.add_widget(copy_btn)

    def copy_task_id(self, task_id):
        Clipboard.copy(str(task_id))
        popup = Popup(
            title='ID Copiado',
            content=Label(text=f'ID {task_id} copiado para a área de transferência!'),
            size_hint=(None, None),
            size=(300, 200)
        )
        popup.open()

    def refresh_tasks(self):
        def refresh_tasks_thread():
            try:
                response = requests.get('http://localhost:8000/tasks/')
                if response.status_code == 200:
                    tasks = response.json()
                    Clock.schedule_once(lambda dt: self.update_table(tasks))
                else:
                    Clock.schedule_once(lambda dt: self.show_error('Erro ao carregar tarefas'))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_error(f'Erro ao carregar tarefas: {str(e)}'))
            finally:
                Clock.schedule_once(lambda dt: self.hide_loading())
        
        self.show_loading()
        threading.Thread(target=refresh_tasks_thread).start()

class UpdateScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        title = Label(
            text='Atualizar Tarefa',
            size_hint_y=None,
            height=50,
            font_size=24
        )
        layout.add_widget(title)
        
        form = GridLayout(cols=2, spacing=10, size_hint_y=None, height=200)
        
        form.add_widget(Label(text='ID da Tarefa:'))
        self.id_input = TextInput(multiline=False)
        self.id_input.bind(text=self.load_task_data)
        form.add_widget(self.id_input)
        
        form.add_widget(Label(text='Novo Título:'))
        self.title_input = TextInput(multiline=False)
        form.add_widget(self.title_input)
        
        form.add_widget(Label(text='Nova Descrição:'))
        self.description_input = TextInput(multiline=True)
        form.add_widget(self.description_input)
        
        form.add_widget(Label(text='Novo Status:'))
        self.status_input = Spinner(
            text='Selecione um status',
            values=('pendente', 'concluido', 'em andamento'),
            size_hint_y=None,
            height=40
        )
        form.add_widget(self.status_input)
        
        layout.add_widget(form)
        
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        back_btn = Button(
            text='Voltar ao Menu',
            background_color=(0.7, 0.7, 0.7, 1)
        )
        back_btn.bind(on_press=self.go_to_menu)
        
        update_btn = Button(
            text='Atualizar Tarefa',
            background_color=(0.9, 0.6, 0.2, 1)
        )
        update_btn.bind(on_press=self.update_task)
        
        button_layout.add_widget(back_btn)
        button_layout.add_widget(update_btn)
        
        layout.add_widget(button_layout)
        self.add_widget(layout)

    def go_to_menu(self, instance):
        self.manager.current = 'menu'
    
    def load_task_data(self, instance, value):
        if value:
            def load_task_thread():
                try:
                    Clock.schedule_once(self.show_loading)
                    response = requests.get(f'http://localhost:8000/tasks/{value}')
                    if response.status_code == 200:
                        task = response.json()
                        def update_form(dt):
                            self.title_input.text = task['title']
                            self.description_input.text = task['description']
                            self.status_input.text = task['status']
                        Clock.schedule_once(update_form)
                except Exception as e:
                    print(f"Erro ao carregar dados da tarefa: {e}")
                finally:
                    Clock.schedule_once(self.hide_loading)
            
            threading.Thread(target=load_task_thread).start()
    
    def update_task(self, instance):
        def update_task_thread():
            try:
                Clock.schedule_once(self.show_loading)
                task_id = self.id_input.text
                if not task_id:
                    return
                
                response = requests.get(f'http://localhost:8000/tasks/{task_id}')
                if response.status_code != 200:
                    return
                
                current_task = response.json()
                
                data = {
                    'title': self.title_input.text if self.title_input.text else current_task['title'],
                    'description': self.description_input.text if self.description_input.text else current_task['description'],
                    'status': self.status_input.text if self.status_input.text else current_task['status']
                }
                
                response = requests.put(f'http://localhost:8000/tasks/{task_id}', json=data)
                if response.status_code == 200:
                    def on_success(dt):
                        self.clear_form()
                        self.manager.get_screen('list').refresh_tasks()
                        self.manager.current = 'list'
                    Clock.schedule_once(on_success)
            except Exception as e:
                print(f"Erro ao atualizar tarefa: {e}")
            finally:
                Clock.schedule_once(self.hide_loading)
        
        threading.Thread(target=update_task_thread).start()
    
    def clear_form(self):
        self.id_input.text = ''
        self.title_input.text = ''
        self.description_input.text = ''
        self.status_input.text = ''

class DeleteScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        title = Label(
            text='Deletar Tarefa',
            size_hint_y=None,
            height=50,
            font_size=24
        )
        layout.add_widget(title)
        
        form = GridLayout(cols=2, spacing=10, size_hint_y=None, height=100)
        
        form.add_widget(Label(text='ID da Tarefa:'))
        self.id_input = TextInput(multiline=False)
        form.add_widget(self.id_input)
        
        layout.add_widget(form)
        
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        back_btn = Button(
            text='Voltar ao Menu',
            background_color=(0.7, 0.7, 0.7, 1)
        )
        back_btn.bind(on_press=self.go_to_menu)
        
        delete_btn = Button(
            text='Deletar Tarefa',
            background_color=(0.9, 0.2, 0.2, 1)
        )
        delete_btn.bind(on_press=self.delete_task)
        
        button_layout.add_widget(back_btn)
        button_layout.add_widget(delete_btn)
        
        layout.add_widget(button_layout)
        self.add_widget(layout)
    
    def go_to_menu(self, instance):
        self.manager.current = 'menu'
    
    def delete_task(self, instance):
        def delete_task_thread():
            try:
                Clock.schedule_once(self.show_loading)
                task_id = self.id_input.text
                if not task_id:
                    return
                    
                response = requests.delete(f'http://localhost:8000/tasks/{task_id}')
                if response.status_code == 200:
                    def on_success(dt):
                        self.id_input.text = ''
                        self.manager.get_screen('list').refresh_tasks()
                        self.manager.current = 'list'
                    Clock.schedule_once(on_success)
            except Exception as e:
                print(f"Erro ao deletar tarefa: {e}")
            finally:
                Clock.schedule_once(self.hide_loading)
        
        threading.Thread(target=delete_task_thread).start()

class TodoApp(App):
    def build(self):
        sm = ScreenManager()
        
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(CreateScreen(name='create'))
        sm.add_widget(ListScreen(name='list'))
        sm.add_widget(UpdateScreen(name='update'))
        sm.add_widget(DeleteScreen(name='delete'))
        
        return sm

if __name__ == '__main__':
    TodoApp().run() 