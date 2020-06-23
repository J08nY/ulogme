
# ulogme


> ### How productive were you today? How much code have you written? Where did your time go?

Keep track of your computer activity throughout the day: visualize your active window titles and the number of keystrokes in beautiful HTML timelines. Current features:

- Records your **active window** title throughout the day
- Records the **frequency of key presses** throughout the day
- Record custom **note annotations** for particular times of day, or for day in general
- Everything runs **completely locally**: none of your data is uploaded anywhere
- **Beautiful, customizable UI** in HTML/CSS/JS (d3js).

## Demo

See a blog post (along with multiple screenshots) describing the project [here](http://karpathy.github.io/2014/08/03/quantifying-productivity/).

**Running**
1. Start the app: `./app.py`
2. Start the collection in using the app indicator that pops up.

**The user interface**

1. **Important**. As a one-time setup, copy over the example settings file to your own copy: `$ cp render/render_settings_example.js render/render_settings.js` to create your own `render_settings.js` settings file. In this file modify everything to your own preferences. Follow the provided example to specify title mappings: A raw window title comes in, and we match it against regular expressions to determine what type of activity it is. For example, the code would convert "Google Chrome - some cool website" into just "Google Chrome". Follow the provided example and read the comments for all settings in the file.
2. Once that's set up, start the web server viewer: `./serve.py`, and go to to the provided address) for example `http://localhost:8124`) in your browser. Hit the refresh button on top right every time you'd like to refresh the results based on most recently recorded activity
3. If your data isn't loading, try to explicitly run `./export_events.py` and then hit refresh. This should only be an issue the very first time you run ulogme.

## User Interface

The user interface can switch between a single day view and an overview view by link on top. You have to hit the refresh button every time you'd like to pull in new data.

#### Single day page

- You can enter a reminder "blog" on top if you'd like to summarize the day for yourself or enter other memos.
- Click on any bar in the *barcode view* to enter a custom (short) note snippet for the time when the selected activity began. I use this to mark meetings, track my coffee/food intake, sleep time, or my total time spent running/swimming/gym or to leave notes for certain patterns of activity, etc. These could all later be correlated with various measures of productivity, in future.

#### Overview page

- You can click the window titles to toggle them on and off from the visualization 
- Clicking on the vertical bars takes you to the full statistics for that day.
