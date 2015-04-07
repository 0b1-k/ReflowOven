#!/usr/bin/python
import curses

class LCD(object):
    def __init__(self):
        try:
            self.__stdscr = curses.initscr()
        except Exception:
            self.__stdscr = None
            
        if (self.__stdscr is not None):
            curses.noecho()
            curses.cbreak()
            self.__stdscr.keypad(1)
        
    def Cleanup(self):
        if (self.__stdscr is not None):
            self.__stdscr.keypad(0)
            curses.nocbreak()
            curses.echo()
            curses.endwin()
    
    def Clear(self):
        if (self.__stdscr is not None):
            self.__stdscr.clear()
    
    def SetCursor(self, column, line):
        if (self.__stdscr is not None):
            self.__stdscr.move(line, column)

    def Print(self, msg):
        if (self.__stdscr is not None):
            self.__stdscr.addstr(msg)
            self.__stdscr.refresh()
        else:
            print(msg)

if __name__ == '__main__':
    lcd = LCD()
    try:
        while True:
            lcd.Clear()
            lcd.SetCursor(0, 0)
            lcd.Print("Line 0")
            lcd.SetCursor(0, 1)
            lcd.Print("Line 1")
    except KeyboardInterrupt as e:
        pass
    lcd.Cleanup()
