
### Lawnscaper - A level editor for Lawn Mower by serakeri

![lawnscaper preview](https://raw.githubusercontent.com/serakeri/Lawnscaper/screenshot/lawnscaper.png)

### How to run

This level editor was written for python 3. If you don't have python 3 then
install it from python.org. Once installed drag `lawnscaper.py` to python.exe.
You will be prompted to load the `lawn_mower.nes` rom and then use the below controls.

### Note

255 is the max amount of grass that can be mowed before the level goal is met.<br />
If more than 255 grass is placed on a level then the stage will be complete before fully mowed.<br />
The total grass is shown in the title bar while editing.

### Controls

<pre>
Ctrl+S          Save changes to rom. You will be prompted where to save the new rom.<br />
Right Click     Set spawn point
Left Click      Draw the current selected tile brush
1               Select mowed grass tile brush
2               Select unmowed grass tile brush
3               Select flower tile brush
4               Select rock tile brush
Page Up
or Up Arrow     Go to previous level
Page Down
or Down Arrow   Go to next level
NumPad-
or Left Arrow   Decrease width of current level
NumPad+
or Right Arrow  Increase width of current level
i               Toggle show images
g               Toggle show grid
a               Toggle flower animation

</pre>
