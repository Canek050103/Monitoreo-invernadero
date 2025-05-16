import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import os
import sys
from PIL import Image, ImageTk
import threading


os.makedirs("graficas", exist_ok=True)
os.makedirs("img", exist_ok=True)

ICONO_TAMANO = (300, 300)


def verificar_graficas_guardadas(fecha):
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    ruta_graficas = os.path.join(ruta_base, "graficas")

    for nodo in range(1, 5):
        filename = os.path.join(ruta_graficas, f"grafica_nodo{nodo}_{fecha}.png")
        if not os.path.exists(filename):
            return False
    return True

 
def verificar_y_guardar_dia_anterior():
    ayer = datetime.date.today() - datetime.timedelta(days=1)
    if not verificar_graficas_guardadas(ayer):
        print(f"?? Las graficas del dia {ayer} no fueron guardadas. Guardando ahora...")
        guardar_grafica(ayer)
    else:
        print(f"? Las graficas del dia {ayer} ya estan guardadas.")
 
 

def obtener_datos(nodo=None):
    conn = sqlite3.connect("datos_sensores.db")
    cursor = conn.cursor()

    if nodo is not None:
        cursor.execute("SELECT marca_tiempo, temperatura, humedad FROM sensores WHERE nodo = ? ORDER BY marca_tiempo DESC", (nodo,))
    else:
        cursor.execute("SELECT marca_tiempo, temperatura, humedad FROM sensores")

    datos = cursor.fetchall()
    conn.close()
    
    datos_procesados = []
    for marca_tiempo, temperatura, humedad in datos:
        if len(marca_tiempo) == 8 and marca_tiempo.count(":") == 2:
            hora = marca_tiempo[:5]
        else:
            try:
                hora = datetime.datetime.strptime(marca_tiempo, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            except Exception as e:
                hora = "??:??"
                print("Error con marca de tiempo:", marca_tiempo, "| Error:", e)
        datos_procesados.append((hora, temperatura, humedad))

    return datos_procesados


def guardar_grafica(fecha=None, intervalo=30):
    from matplotlib import dates as mdates
    conn = sqlite3.connect("datos_sensores.db")
    cursor = conn.cursor()

    if fecha is None:
        fecha = datetime.date.today()

    for nodo in range(1, 5):
        query = f"""
            SELECT marca_tiempo, temperatura, humedad
            FROM sensores
            WHERE nodo = ? AND date(marca_tiempo) = ?
            ORDER BY marca_tiempo ASC
        """
        cursor.execute(query, (nodo, fecha))
        datos = cursor.fetchall()

        if datos:
            datos_filtrados = []
            ultima_hora = None

            for marca_tiempo, temp, hum in datos:
                try:
                    dt = datetime.datetime.strptime(marca_tiempo, "%Y-%m-%d %H:%M:%S")
                except:
                    continue

                if ultima_hora is None or (dt - ultima_hora).total_seconds() >= intervalo * 60:
                    datos_filtrados.append((dt, temp, hum))
                    ultima_hora = dt

            if not datos_filtrados:
                continue

            horas_dt, temperaturas, humedades = zip(*datos_filtrados)

            fig, ax1 = plt.subplots(figsize=(14, 8))
            ax2 = ax1.twinx()

            ax1.plot(horas_dt, temperaturas, 'ro-', label=f"Temperatura Nodo {nodo} (C)")
            ax2.plot(horas_dt, humedades, 'bo-', label=f"Humedad Nodo {nodo} (%)")

            ax1.set_xlabel("Hora", fontsize=15)
            ax1.set_ylabel("Temperatura (C)", color="red", fontsize=18)
            ax2.set_ylabel("Humedad (%)", color="blue", fontsize=18)

            ax1.tick_params(axis='y', labelsize=14, labelcolor="red")
            ax2.tick_params(axis='y', labelsize=14, labelcolor="blue")
            ax1.tick_params(axis='x', labelsize=12, rotation=45)

            ax1.xaxis.set_major_locator(mdates.MinuteLocator(interval=intervalo))
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

            ax1.set_title(f"Datos del nodo {nodo} - {fecha}", fontsize=20)
            ax1.grid(True)

            lineas_1, etiquetas_1 = ax1.get_legend_handles_labels()
            lineas_2, etiquetas_2 = ax2.get_legend_handles_labels()
            ax1.legend(lineas_1 + lineas_2, etiquetas_1 + etiquetas_2, loc='upper left')

            fig.autofmt_xdate()

            ruta_base = os.path.dirname(os.path.abspath(__file__))
            ruta_graficas = os.path.join(ruta_base, "graficas")
            os.makedirs(ruta_graficas, exist_ok=True)

            filename = os.path.join(ruta_graficas, f"grafica_nodo{nodo}_{fecha}.png")
            plt.savefig(filename, bbox_inches='tight')
            plt.close()

    conn.close()




def cargar_imagen(ruta, size=ICONO_TAMANO):
    try:
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        ruta_completa = os.path.join(ruta_base, "img", ruta)
        img = Image.open(ruta_completa)
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print("Error al cargar imagen", ruta, ":", e)
        img = Image.new("RGB", size, color="gray")
        return ImageTk.PhotoImage(img)


class CompararNodos(tk.Frame):
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller
        tk.Label(self, text="Comparacion entre Nodos", font=("Arial", 28)).pack(pady=20)

        self.fig, self.ax = plt.subplots(figsize=(14, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack()

        self.mostrar_comparacion()

        tk.Button(self, text="Volver", font=("Arial", 28),
                  command=lambda: controller.mostrar_frame(MenuPrincipal)).pack(pady=20)

    def mostrar_comparacion(self):
        self.ax.clear()
        colores = ['red', 'blue', 'green', 'orange']
        for nodo in range(1, 5):
            datos = sorted(obtener_datos(nodo), key=lambda x: x[0])
            if datos:
                hoy = datetime.date.today()
                horas_str, temp, _ = zip(*datos)
                horas_dt = [datetime.datetime.strptime(f"{hoy} {h}", "%Y-%m-%d %H:%M") for h in horas_str]
                self.ax.plot(horas_dt, temp, label=f"Nodo {nodo}", color=colores[nodo - 1])

        self.ax.set_title("Comparacion de Temperaturas", fontsize=24)
        self.ax.set_xlabel("Hora")
        self.ax.set_ylabel("Temperatura (C)")
        self.ax.legend()
        self.ax.grid(True)
        self.fig.autofmt_xdate()
        self.canvas.draw()




class InterfazSensores(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Monitoreo")
        self.attributes("-zoomed", True)  
        self.overrideredirect(True)
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.configure(background="white")
        self.bind("<Escape>", lambda event: self.destroy())

        self.frames = {}
        self.mostrar_frame(MenuPrincipal)

    def mostrar_frame(self, frame_class):
        if frame_class not in self.frames:
            self.frames[frame_class] = frame_class(self)
            self.frames[frame_class].place(relx=0.5, rely=0.5, anchor="center")  
        
        for frame in self.frames.values():
            frame.place_forget()
        
        self.frames[frame_class].place(relx=0.5, rely=0.5, anchor="center")

class MenuPrincipal(tk.Frame):
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller
        tk.Label(self, text="INVERNADERO SANTAGRO", font=("Arial", 24)).pack(pady=20)

        self.imagen_tiempo_real = cargar_imagen("tiempo_real.png")
        self.imagen_grafica = cargar_imagen("grafica.jfif")
        self.imagen_compa = cargar_imagen("grafica_2.jfif")
        self.imagen_guardar = cargar_imagen("guardar.png")
        self.imagen_salir = cargar_imagen("salida.jpg")
        

        button_frame = tk.Frame(self)
        button_frame.pack(pady=30)

        botones = [
            (self.imagen_tiempo_real, "Tiempo Real", DatosTiempoReal),
            (self.imagen_grafica, "Variaciones del dia", Graficas),
           (self.imagen_compa, "Comparar Nodos", CompararNodos), 
            (self.imagen_guardar, "Graficas guardadas", ImagenesGuardadas),
            (self.imagen_salir, "Salir", None)
        ]

        for img, text, frame in botones:
            frame_btn = tk.Frame(button_frame)
            frame_btn.pack(side="left", padx=30, pady=15)
            if frame:
                btn = tk.Button(frame_btn, image=img, command=lambda f=frame: controller.mostrar_frame(f))
            else:
                btn = tk.Button(frame_btn, image=img, command=self.controller.destroy)
            btn.pack()
            tk.Label(frame_btn, text=text, font=("Arial", 30)).pack()
class DatosTiempoReal(tk.Frame):
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller
        tk.Label(self, text="Datos en Tiempo Real", font=("Arial", 28)).pack(pady=20)
        
        frame_zonas = tk.Frame(self)
        frame_zonas.pack()
        
        frame_temperatura = tk.Frame(frame_zonas)
        frame_temperatura.grid(row=0, column=0, padx=10, pady=10)
        self.canvas_temp = []
        self.labels_temp = []
        
        for i in range(2):
            for j in range(2):
                nodo = i*2 + j + 1
                canvas = tk.Canvas(frame_temperatura, width=200, height=200, bg="white")
                canvas.grid(row=i, column=j, padx=5, pady=5)
                self.canvas_temp.append(canvas)
                
                label = tk.Label(frame_temperatura, text="", font=("Arial", 12))
                label.grid(row=i+2, column=j)
                self.labels_temp.append(label)
        
        tk.Label(frame_temperatura, text="Zonas de Temperatura", font=("Arial", 20)).grid(row=4, column=0, columnspan=2)
        frame_humedad = tk.Frame(frame_zonas)
        frame_humedad.grid(row=0, column=1, padx=10, pady=10)
        self.canvas_hum = []
        self.labels_hum = []
        
        for i in range(2):
            for j in range(2):
                nodo = i*2 + j + 1
                canvas = tk.Canvas(frame_humedad, width=200, height=200, bg="white")
                canvas.grid(row=i, column=j, padx=5, pady=5)
                self.canvas_hum.append(canvas)
                
                label = tk.Label(frame_humedad, text="", font=("Arial", 12))
                label.grid(row=i+2, column=j)
                self.labels_hum.append(label)
        
        tk.Label(frame_humedad, text="Zonas de Humedad", font=("Arial", 20)).grid(row=4, column=0, columnspan=2)
        legend_frame = tk.Frame(self)
        legend_frame.pack(pady=10)
        tk.Label(legend_frame, text="Temperatura: Verde = Ideal (18-25 C), Rojo = Alta (>25 C), Azul = Baja (<18 C)", 
                font=("Arial", 20)).pack()
        tk.Label(legend_frame, text="Humedad: Verde = Ideal (40-70%), Rojo = Alta (>70%), Azul = Baja (<40%)", 
                font=("Arial", 20)).pack()
        
        tk.Button(self, text="Volver", font=("Arial", 24), padx=30, pady=20,
                command=lambda: controller.mostrar_frame(MenuPrincipal)).pack(pady=10)        
        self.actualizar_mapa()
    def actualizar_mapa(self):
        for nodo in range(1, 5):
            datos = obtener_datos(nodo)
            if datos:
                hora, temp, hum = datos[0]                
                color_temp = "green" if 18 <= temp <= 25 else "red" if temp > 25 else "blue"
                color_hum = "green" if 40 <= hum <= 70 else "red" if hum > 70 else "blue"
                
                self.canvas_temp[nodo-1].delete("all")
                self.canvas_temp[nodo-1].create_rectangle(0, 0, 200, 200, fill=color_temp)
                self.canvas_temp[nodo-1].create_text(100, 100, text=f"Nodo {nodo}\n{temp}  C", 
                                                    font=("Arial", 20), fill="white")
                self.labels_temp[nodo-1].config(text=f"Ultima actualizacion: {hora}")
                
                self.canvas_hum[nodo-1].delete("all")
                self.canvas_hum[nodo-1].create_rectangle(0, 0, 200, 200, fill=color_hum)
                self.canvas_hum[nodo-1].create_text(100, 100, text=f"Nodo {nodo}\n{hum}%", 
                                                  font=("Arial", 20), fill="white")
                self.labels_hum[nodo-1].config(text=f"Ultima actualizacion: {hora}")
        
        self.after(5000, self.actualizar_mapa)
class Graficas(tk.Frame):
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller

        control_frame = tk.Frame(self)
        control_frame.pack(pady=10)

        intervalo_frame = tk.Frame(self)
        intervalo_frame.pack(pady=(0,10))

        tk.Label(intervalo_frame, text="Intervalo (min):", font=("Arial", 20)).pack(side="left", padx=10)

        self.intervalo_var = tk.IntVar(value=30)

        botones_intervalo = tk.Frame(intervalo_frame)
        botones_intervalo.pack(side="left")

        for valor in [5, 10, 15, 30, 60]:
            tk.Button(botones_intervalo, text=str(valor), font=("Arial", 22), width=4,
                      command=lambda v=valor: self.set_intervalo(v)).pack(side="left", padx=5)

        tk.Label(control_frame, text="Seleccionar nodo:", font=("Arial", 28)).pack(side="left")

        self.nodo_var = tk.IntVar(value=1)
        for i in range(1, 5):
            tk.Radiobutton(control_frame, text=f"Nodo {i}", variable=self.nodo_var,
                          value=i, font=("Arial", 32), command=self.mostrar_grafica).pack(side="left", padx=10)

        tk.Label(self, text="Graficas de Sensores", font=("Arial", 22)).pack(pady=10)

        self.fig, self.ax = plt.subplots(figsize=(14, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(pady=20)

        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Guardar Grafica", font=("Arial", 34),
                 command=guardar_grafica).pack(side="left", padx=20)
        tk.Button(button_frame, text="Volver", font=("Arial", 34),
                  command=lambda: controller.mostrar_frame(MenuPrincipal)).pack(side="left", padx=20)

        self.mostrar_grafica()

    def set_intervalo(self, valor):
        self.intervalo_var.set(valor)
        self.mostrar_grafica()
        
    def mostrar_grafica(self):
        from matplotlib import dates as mdates
        nodo = self.nodo_var.get()
        intervalo = self.intervalo_var.get()
        datos_crudos = sorted(obtener_datos(nodo), key=lambda x: x[0])

        if datos_crudos:
            hoy = datetime.date.today()
            datos_filtrados = []
            ultima_hora = None

            for hora_str, temp, hum in datos_crudos:
                try:
                    dt = datetime.datetime.strptime(f"{hoy} {hora_str}", "%Y-%m-%d %H:%M")
                except:
                    continue

                if ultima_hora is None or (dt - ultima_hora).total_seconds() >= intervalo * 60:
                    datos_filtrados.append((dt, temp, hum))
                    ultima_hora = dt

            if not datos_filtrados:
                self.ax.clear()
                self.ax.set_title("No hay datos suficientes con ese intervalo", fontsize=20)
                self.canvas.draw()
                return

            horas_dt, temperaturas, humedades = zip(*datos_filtrados)

            self.fig.clf()
            self.ax = self.fig.add_subplot(111)
            self.ax2 = self.ax.twinx()

            self.ax.plot(horas_dt, temperaturas, 'ro-', label=f"Temperatura Nodo {nodo} (C)")
            self.ax2.plot(horas_dt, humedades, 'bo-', label=f"Humedad Nodo {nodo} (%)")

            self.ax.set_xlabel("Hora", fontsize=15)
            self.ax.set_ylabel("Temperatura (C)", color="red", fontsize=18)
            self.ax2.set_ylabel("Humedad (%)", color="blue", fontsize=18)

            self.ax.tick_params(axis='y', labelsize=18, labelcolor="red")
            self.ax2.tick_params(axis='y', labelsize=18, labelcolor="blue")
            self.ax.tick_params(axis='x', labelsize=18, labelrotation=45)

            self.ax.set_title(f"Datos del nodo {nodo} - {datetime.date.today()}", fontsize=28)

            self.ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=intervalo))
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

            lineas_1, etiquetas_1 = self.ax.get_legend_handles_labels()
            lineas_2, etiquetas_2 = self.ax2.get_legend_handles_labels()
            self.ax.legend(lineas_1 + lineas_2, etiquetas_1 + etiquetas_2, loc='upper left')

            self.ax.grid(True)
            self.fig.autofmt_xdate()
        else:
            self.ax.clear()
            self.ax.set_title("No hay datos disponibles", fontsize=20)

        self.canvas.draw()
 


class ImagenesGuardadas(tk.Frame):
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller
        tk.Label(self, text="Imagenes Guardadas", font=("Arial", 26)).pack(pady=20)
        
        self.index = 0
        self.imagen_label = tk.Label(self)
        self.imagen_label.pack()
        self.actualizar_lista_imagenes()

        
        control_frame = tk.Frame(self)
        control_frame.pack(pady=20)
        
        tk.Button(control_frame, text="Anterior", font=("Arial", 30), 
                 command=self.anterior_imagen).pack(side="left", padx=20)
        tk.Button(control_frame, text="Siguiente", font=("Arial", 30), 
                 command=self.siguiente_imagen).pack(side="left", padx=20)
        tk.Button(control_frame, text="Actualizar Lista", font=("Arial", 30), 
                 command=self.actualizar_lista_imagenes).pack(side="left", padx=20)
        
        tk.Button(self, text="Volver", font=("Arial", 32), 
                 command=lambda: controller.mostrar_frame(MenuPrincipal)).pack(pady=10)
        if self.lista_imagenes:
            self.mostrar_imagen()
        else:
            self.imagen_label.config(text="No hay imagenes guardadas", font=("Arial", 24))
    
    def actualizar_lista_imagenes(self):
        self.lista_imagenes = [f for f in os.listdir("graficas") if f.endswith(('.png', '.jpg', '.jpeg'))]
        self.lista_imagenes.sort(reverse=True)  
        self.index = 0
        if self.lista_imagenes:
            self.mostrar_imagen()
        else:
            self.imagen_label.config(text="No hay imagenes guardadas", font=("Arial", 24))
    
    def mostrar_imagen(self):
        if self.lista_imagenes:
            ruta_imagen = os.path.join("graficas", self.lista_imagenes[self.index])
            try:
                img = Image.open(ruta_imagen)
                img = img.resize((1150, 800), Image.LANCZOS)
                self.imagen_tk = ImageTk.PhotoImage(img)
                self.imagen_label.config(image=self.imagen_tk)
                
            except Exception as e:
                print(f"Error al cargar imagen: {e}")
                self.imagen_label.config(text=f"Error al cargar imagen: {self.lista_imagenes[self.index]}", 
                                       font=("Arial", 24))
    def anterior_imagen(self):
        if self.lista_imagenes:
            self.index = (self.index - 1) % len(self.lista_imagenes)
            self.mostrar_imagen()
    
    def siguiente_imagen(self):
        if self.lista_imagenes:
            self.index = (self.index + 1) % len(self.lista_imagenes)
            self.mostrar_imagen()

if __name__ == "__main__":
    verificar_y_guardar_dia_anterior() 
    app = InterfazSensores()
    app.mainloop()

