import time
import datetime
import logging
import json
# for error tracing
import traceback
# to save and load cookies
import pickle

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

with open('data/user_account.json') as json_data:
    USER_ACCOUNT = json.load(json_data)

with open('data/group_list.json') as json_data:
    GROUP_LIST = json.load(json_data)

LINK_LOGIN = 'https://secure.meetup.com/login/'
LINK_EVENT_LIST = 'https://www.meetup.com/{}/events/'
APP_NAME = 'meetupAutoRSVP'
COOKIES_FILE_NAME = 'cookies.pkl'
CONFIG_HIDE_PROCESS = True
CONFIG_HIDE_IMAGES = True
CHECK_TIME_SECOND = 40


# setting up and init of logging and selenium
def setup():
    # logging setup
    logging.basicConfig(filename='{}.log'.format(APP_NAME), level=logging.DEBUG, format='%(asctime)s %(message)s')

    # selenium setup to not open chrome windows
    chrome_options = Options()
    if CONFIG_HIDE_PROCESS:
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")

    if CONFIG_HIDE_IMAGES:
        sub_options = {'profile.default_content_setting_values': {'cookies': 2, 'images': 2, 'javascript': 2,
                                                            'plugins': 2, 'popups': 2, 'geolocation': 2,
                                                            'notifications': 2, 'auto_select_certificate': 2,
                                                            'fullscreen': 2,
                                                            'mouselock': 2, 'mixed_script': 2, 'media_stream': 2,
                                                            'media_stream_mic': 2, 'media_stream_camera': 2,
                                                            'protocol_handlers': 2,
                                                            'ppapi_broker': 2, 'automatic_downloads': 2, 'midi_sysex': 2,
                                                            'push_messaging': 2, 'ssl_cert_decisions': 2,
                                                            'metro_switch_to_desktop': 2,
                                                            'protected_media_identifier': 2, 'app_banner': 2,
                                                            'site_engagement': 2,
                                                            'durable_storage': 2}}
        chrome_options.add_experimental_option('prefs', sub_options)
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")

    # selenium INIT
    browser = webdriver.Chrome(options=chrome_options)
    return browser


# console message and logging
def alert_message(message, is_error=False):
    time_now = datetime.datetime.now()
    message = "CUSTOM MESSAGE {}".format(str(message))
    if is_error is True:
        # add traceback for debugging if error
        message = "{} {}".format(message, traceback.format_exc())
        logging.error(message)
    else:
        logging.info(message)
    print("{}: {}".format(time_now, message))


# return the updated link to event list with group name in it
def get_link_event_list():
    return LINK_EVENT_LIST.format(GROUP_LIST[0])


# login using old cookie, no need to re login
def cookies_load(browser):
    browser.get(LINK_LOGIN)
    try:
        for cookie in pickle.load(open(COOKIES_FILE_NAME, "rb")):
            browser.add_cookie({k: cookie[k] for k in ('name', 'value', 'domain', 'path') if k in cookie})
    except FileNotFoundError:
        alert_message('No cookies yet')
    browser.get(LINK_LOGIN)


# save cookies for next use
def cookies_save(browser):
    browser.get(get_link_event_list())
    pickle.dump(browser.get_cookies(), open(COOKIES_FILE_NAME, "wb"))


# login using old cookie, no need to re login
def login(browser):
    alert_message("Logging in.")
    elem = browser.find_element_by_id("email")
    elem.send_keys(USER_ACCOUNT.USER_NAME)
    elem = browser.find_element_by_id("password")
    elem.send_keys(USER_ACCOUNT.PASSWORD)
    elem.send_keys(Keys.RETURN)


# exit all
def close_everything(browser):
    alert_message("Exit.")
    browser.close()
    exit()


# check if there are one upcoming event
def new_coming_event_count(browser):
    browser.get(get_link_event_list())
    return len(browser.find_elements_by_css_selector('.list-item'))


# check if the event available (not cancelled)
def is_event_available(browser):
    return len(browser.find_elements_by_css_selector('.eventTimeDisplay.text--strikethrough')) == 0


# go to the event link, click RSVP and check if RSVP works
def rsvp(browser):
    # go to the event link
    event_button = browser.find_elements_by_css_selector('.eventList-list .eventCardHead--title')
    event_link = event_button[0].get_attribute("href")
    browser.get(event_link)

    # click RSVP
    browser.find_elements_by_css_selector('.rsvpIndicator-button')[0].click()

    # check if RSVP
    browser.get(event_link)
    alert_message('event link: {}'.format(event_link))
    return len(browser.find_elements_by_css_selector('.rsvpIndicator-button')) != 0


def main():
    # setting up and init of logging and selenium
    browser = setup()

    # login using old cookie, no need to re login
    cookies_load(browser)

    # check is the cookie working, otherwise login
    if browser.find_elements_by_css_selector('#globalNav.authenticated'):
        alert_message("Cookies work, no login needed.")
    else:
        # login
        login(browser)

    # save cookies for next use
    cookies_save(browser)

    count_try = 0
    # looping each time to check
    while True:
        try:
            # counter
            count_try += 1

            # check if there are one upcoming event
            list_event_count = new_coming_event_count(browser)

            # if there is no event
            if list_event_count < 1:
                alert_message('{} No event is found. Keep waiting!'.format(count_try))

            # if there are multiple events to choose
            elif list_event_count > 1:
                alert_message('There are {} events. System only works for one event in group'.format(list_event_count))
                # exit all
                close_everything(browser)

            # if correct, there is one upcoming event
            else:
                alert_message('One event is available!')

                # check if the event available (not cancelled)
                is_available = is_event_available(browser)

                if is_available is False:
                    alert_message('But it has been cancelled.')

                else:
                    # go to the event link, click RSVP and check if RSVP works
                    is_rsvp_success = rsvp(browser)

                    if is_rsvp_success:
                        alert_message('Congrats! You got the RSVP!')
                    else:
                        alert_message('Sorry, RSVP is failed', True)

                # exit all
                close_everything(browser)

            # sleep before re action
            time.sleep(CHECK_TIME_SECOND)

        # exit
        except KeyboardInterrupt:
            # exit all
            close_everything(browser)

        # other unknown error
        except Exception as e:
            alert_message("{}".format(e), True)
            # exit all
            close_everything(browser)


if __name__ == '__main__':
    main()