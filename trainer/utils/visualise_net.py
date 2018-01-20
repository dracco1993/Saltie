from tkinter import *
import numpy as np
import ast

# Some values useful for editing how the net gets shown
x_spacing = 100
y_spacing = 50
circle_dia = 30


class Visualiser:
    gui = None  # The window
    relu = None  # Whether activations are through relu
    highrelu = 20  # The
    bigweight = 30
    layer_activations = None  # The values for the activations
    scale = 1.0  # The current scale of the canvas
    delta = 0.75  # The impact of scrolling
    biggestarraylen = 0  # For aligning all the layers
    eFrame = None  # The frame with the customisation
    iFrame = None  # The frame with the info
    cFrame = None  # The frame with the canvas
    canvas = None  # The canvas showing the net
    rotate_canvas = False  # Should the canvas be rotated

    info_text_neuron = None  # The info about the last neuron hovered over
    info_text_line = None  # The info about the last line (connection) hovered over

    input_array = None  # The StringVar storing the array used when hitting generate
    input_relu = None  # The StringVar storing the array used for the relu adaption
    relu_number = None  # The IntVar storing the spinbox value


    def __init__(self, inp=None):
        # Initialising the window
        self.gui = Tk()
        self.gui.geometry('600x600')
        self.gui.title("Net visualisation")

        # Initialising all variables
        self.highrelu = 20
        self.relu = [True, True, True, True, False]  # Is the layer using relu
        self.bigweight = 30
        self.layer_activations = inp
        # del inp (Is it necessary? Might kill the original array as well, creating problems over there)
        self.rotate_canvas = False
        self.last_layer = list()
        self.scale = 1.0
        self.delta = 0.75
        self.biggestarraylen = 0
        for item in self.layer_activations:
            if len(item) > self.biggestarraylen:
                self.biggestarraylen = len(item)

        # Initialising the frames
        self.eFrame = Frame(self.gui)
        self.eFrame.grid(row=0, column=0)
        self.iFrame = Frame(self.gui)
        self.iFrame.grid(row=1, column=0, sticky='nw')
        self.cFrame = Frame(self.gui, bd=1, relief=SUNKEN)
        self.cFrame.grid(row=0, column=1, sticky='nsew', rowspan=2)

        self.config_options()

        self.canvas_stuff()
        self.edit_stuff()
        self.info_stuff()
        mainloop()

    def edit_stuff(self):
        self.input_array = StringVar()
        input_array_field = Entry(self.eFrame, textvariable=self.input_array)
        input_array_field.bind('<Return>', lambda event: self.change_input())
        input_array_field.grid(row=0, column=0)
        input_array_button = Button(self.eFrame, command=self.change_input, text="Generate")
        input_array_button.grid(row=0, column=1)

        self.input_relu = StringVar()
        input_relu_field = Entry(self.eFrame, textvariable=self.input_relu)
        input_relu_field.bind('<Return>', lambda event: self.change_relu())
        input_relu_field.grid(row=1, column=0)
        input_relu_button = Button(self.eFrame, command=self.change_relu, text="Edit relu")
        input_relu_button.grid(row=1, column=1)

        self.relu_number = IntVar()
        self.relu_number.set(20)
        relu_spin_box = Spinbox(self.eFrame, from_=1, to=1000, width=5, textvariable=self.relu_number)
        relu_spin_box.bind('<Return>', lambda event: self.change_relu_factor())
        relu_spin_box.grid(row=2, column=0)
        relu_button = Button(self.eFrame, command=self.change_relu_factor, text="Change high relu")
        relu_button.grid(row=2, column=1)

        rotate = Button(self.eFrame, command=self.rotate_and_refresh, text="Rotate")
        rotate.grid(row=3, column=0)

    def info_stuff(self):
        self.info_text_neuron = StringVar()
        self.info_text_neuron.set("Layer: ?\nNeuron: ?\nActivation type: ?\nActivation: ?")
        activation_label = Label(self.iFrame, textvariable=self.info_text_neuron, justify=LEFT)
        activation_label.grid(row=0, column=0, sticky='w')

        self.info_text_line = StringVar()
        self.info_text_line.set("From:\nLayer: ?\nNeuron: ?\nTo:\nLayer: ?\nNeuron: ?")
        activation_label = Label(self.iFrame, textvariable=self.info_text_line, justify=LEFT)
        activation_label.grid(row=1, column=0, sticky='w')

    def canvas_stuff(self):
        # Create canvas including the scrollbars
        class AutoScrollbar(Scrollbar):
            def set(self, lo, hi):
                if float(lo) <= 0.0 and float(hi) >= 1.0:
                    self.grid_remove()
                else:
                    self.grid()
                Scrollbar.set(self, lo, hi)

        def wheel(event):
            scale = 1.0
            # Respond to Linux (event.num) or Windows (event.delta) wheel event
            if event.num == 5 or event.delta == -120:
                scale *= self.delta
                self.scale *= self.delta
            if event.num == 4 or event.delta == 120:
                scale /= self.delta
                self.scale /= self.delta
            # Rescale all canvas objects
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.canvas.scale('all', x, y, scale, scale)
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        vbar = AutoScrollbar(self.cFrame, orient='vertical')
        hbar = AutoScrollbar(self.cFrame, orient='horizontal')
        vbar.grid(row=0, column=1, sticky='ns')
        hbar.grid(row=1, column=0, sticky='we')
        self.canvas = Canvas(self.cFrame, xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        vbar.configure(command=self.canvas.yview)  # bind scrollbars to the canvas
        hbar.configure(command=self.canvas.xview)

        # Bind events to the Canvas
        self.canvas.bind('<Button-1>', lambda event: self.canvas.scan_mark(event.x, event.y))
        self.canvas.bind('<B1-Motion>', lambda event: self.canvas.scan_dragto(event.x, event.y, gain=1))
        self.canvas.bind('<MouseWheel>', wheel)
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        # Generate the canvas itself
        if self.layer_activations is not None:
            for i in range(len(self.layer_activations)):
                self.create_layer(i)

    def create_circle(self, x0, y0, activation, relu, layer, neuron):
        if self.rotate_canvas:
            x0, y0 = y0, x0
        if relu:
            activation = activation if activation <= self.highrelu else self.highrelu
            rgb = int(-1 * (activation - self.highrelu) * 255 / self.highrelu)
        else:
            activation = activation if activation <= 1 else 1
            rgb = int(-1 * (activation - 1) * 255)
        hex_color = "#{:02x}{:02x}{:02x}".format(rgb, rgb, rgb)
        tag = str(layer) + ";" + str(neuron)
        self.canvas.create_oval(x0, y0, x0 + circle_dia, y0 + circle_dia, fill=hex_color, tags=tag)

        def handler(event, la=layer, ne=neuron):
            self.info_text_neuron.set("Layer: " + str(la) + "\nNeuron: " + str(ne) + "\nActivation type: " + (
                "Relu" if self.relu[layer] else "Sigmoid") + "\nActivation: " + str(
                self.layer_activations[layer][neuron]))

        self.canvas.tag_bind(tag, "<Motion>", handler)

    def create_line(self, x0, y0, x1, y1, layer0, neuron0, layer1, neuron1):
        if self.rotate_canvas:
            x0, y0, x1, y1 = y0, x0, y1, x1
        half = .5 * circle_dia

        weight = self.obtain_weight()
        r, g, b = 0, 0, 0
        if weight >= 0:
            weight = weight if weight <= self.bigweight else self.bigweight
            r = int(-1 * (weight - self.bigweight) * 255 / self.bigweight)
        else:
            weight = weight if weight >= (-self.bigweight) else (-self.bigweight)
            b = int((weight + self.bigweight) * 255 / self.bigweight)
        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)

        tag = str(layer0) + ";" + str(neuron0) + ";" + str(layer1) + ";" + str(neuron1)
        self.canvas.create_line(x0 + half, y0 + half, x1 + half, y1 + half, fill=hex_color, tags=tag)

        def handler(event, l0=layer0, n0=neuron0, l1=layer1, n1=neuron1):
            self.info_text_line.set(
                "From:\nLayer: " + str(l0) + "\nNeuron: " + str(n0) + "\nTo:\nLayer: " + str(l1) + "\nNeuron: " + str(
                    n1))

        self.canvas.tag_bind(tag, "<Motion>", handler)
        self.canvas.tag_lower(tag)


    def obtain_weight(self):
        return np.random.randint(-30, 30)

    def create_layer(self, layer):
        activations = self.layer_activations[layer]
        x = layer * x_spacing
        y = (self.biggestarraylen - len(activations)) * y_spacing * .5
        this_layer = list()
        neuron = 0
        for i in activations:
            this_layer.append([x, y])
            if layer != 0:
                nn = 0
                for n in self.last_layer:
                    self.create_line(n[0], n[1], x, y, layer - 1, nn, layer, neuron)
                    nn += 1
            self.create_circle(x, y, i, self.relu[layer], layer, neuron)
            y += y_spacing
            neuron += 1
        self.last_layer = this_layer

    def refresh_canvas(self):
        self.canvas.scale('all', 0, 0, 1, 1)
        self.scale = 1
        self.canvas.delete('all')
        for i in range(len(self.layer_activations)):
            self.create_layer(i)

    def rotate_and_refresh(self):
        self.rotate_canvas = not self.rotate_canvas
        self.refresh_canvas()

    def change_relu_factor(self):
        self.highrelu = self.relu_number.get()
        self.refresh_canvas()

    def change_relu(self):
        if self.input_relu.get():
            try:
                self.relu = ast.literal_eval(self.input_relu.get())
                self.refresh_canvas()
            except Exception:
                pass

    def change_input(self):
        if self.input_array.get():
            try:
                self.layer_activations = ast.literal_eval(self.input_array.get())
                self.refresh_canvas()
            except Exception:
                pass

    def config_options(self):
        # Make the canvas expandable
        self.gui.grid_rowconfigure(0, weight=1)
        self.gui.grid_rowconfigure(1, weight=1)
        self.gui.grid_columnconfigure(1, weight=1)
        self.cFrame.grid_rowconfigure(0, weight=1)
        self.cFrame.grid_columnconfigure(0, weight=1)

        self.gui.grid_columnconfigure(0, minsize=100)