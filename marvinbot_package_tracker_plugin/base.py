# -*- coding: utf-8 -*-
from marvinbot.utils import localized_date, get_message
from marvinbot.handlers import CommandHandler, CallbackQueryHandler
from marvinbot.signals import plugin_reload
from marvinbot.plugins import Plugin
from marvinbot.models import User
from marvinbot_package_tracker_plugin.models import TrackedPackage
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup
import logging
import re
import requests

log = logging.getLogger(__name__)


class PackageTrackerPlugin(Plugin):
    def __init__(self):
        super(PackageTrackerPlugin, self).__init__('package_tracker')
        self.couriers = []
        self.config = None
        self.bot = None

    def get_default_config(self):
        return {
            'short_name': self.name,
            'enabled': True,
            'auto_subscribe': False,
            'process_interval': {"minutes": 15},
            'max_num_errors': 10,   # Max consecutive errors before deletion
            'max_days_stalled': 7,  # Max days without updates before deletion
            'response_format': '{date} {time}: {status} @ {loc}',
            'response_format_noloc': '{date} {time}: {status}',
            'bmcargo_baseurl': 'http://erp-online.bmcargo.com/zz/estatus.aspx',
            'bmcargo_pattern': r'^WR01-007\d{6}$',
            'aeropaq_baseurl': 'http://erp-online.aeropaq.com/zz/estatus.aspx',
            'aeropaq_pattern': r'^WR02-\d{7}$',
            'caripack_baseurl': 'http://erp-online.caripack.com/zz/estatus.aspx',
            'caripack_pattern': r'^G02-\d{10}$',
            'liberty_baseurl': 'http://online.libertyexpress.com/zz/estatus.aspx',
            'liberty_pattern': r'^WR01-30\d{7}$',
            'picknsend_baseurl': 'http://online.picknsend.com/zz/estatus.aspx',
            'picknsend_pattern': r'^WR13-\d{9}$',
            'domex_baseurl': 'https://domex-online.iplus.com.do/zz/estatus.aspx',
            'domex_pattern': r'^WR01-000\d{6}$',
        }

    def configure(self, config):
        self.couriers = [
            {
                'name': 'BMCargo',
                'handler': self.handle_bmcargo,
                'pattern': re.compile(config.get('bmcargo_pattern'),
                                      flags=re.IGNORECASE)
            },
            {
                'name': 'Aeropaq',
                'handler': self.handle_aeropaq,
                'pattern': re.compile(config.get('aeropaq_pattern'),
                                      flags=re.IGNORECASE)
            },
            {
                'name': 'Caripack',
                'handler': self.handle_caripack,
                'pattern': re.compile(config.get('caripack_pattern'),
                                      flags=re.IGNORECASE)
            },
            {
                'name': 'Liberty Express',
                'handler': self.handle_liberty,
                'pattern': re.compile(config.get('liberty_pattern'),
                                      flags=re.IGNORECASE)
            },
            {
                'name': 'PickN\'Send',
                'handler': self.handle_picknsend,
                'pattern': re.compile(config.get('picknsend_pattern'),
                                      flags=re.IGNORECASE)
            },
            {
                'name': 'DomEX',
                'handler': self.handle_domex,
                'pattern': re.compile(config.get('domex_pattern'),
                                      flags=re.IGNORECASE)
            }
        ]
        self.config = config

    def setup_handlers(self, adapter):
        self.add_handler(CommandHandler('track', self.on_track_command, command_description='Allows the user to track couriers packages.')
                         .add_argument('id', help='Tracking number (e.g. WR01-001231234).'))
        self.add_handler(CallbackQueryHandler('{}:subscribe'.format(self.name), self.on_subscribe_button))
        self.add_handler(CallbackQueryHandler('{}:unsubscribe'.format(self.name), self.on_unsubscribe_button))

    def setup_schedules(self, adapter):
        process_tracked_packages.plugin = self
        interval = self.config.get('process_interval')
        job = self.adapter.add_job(process_tracked_packages, 'interval', **interval,
                                   id='process_tracked_packages', name='Fetches tracked packages for processing',
                                   replace_existing=True)

    def handle_bmcargo(self, tracking_number):
        base_url = self.config.get('bmcargo_baseurl')
        params = {'id': tracking_number}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            return [None, r.status_code]

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            for td in soup.select("td[class=dxgv]"):
                first_div, second_div = td.select("div")
                status = first_div.select_one("span").contents[0]
                date = second_div.contents[0].strip().replace('.', '-')
                time = second_div.contents[2].strip().upper()

                if len(second_div.contents) >= 4:
                    response_format = self.config.get('response_format')
                    loc = second_div.contents[4].strip() if len(second_div.contents) >= 4 else 'Desconocido'
                    response = response_format.format(status=status, date=date, time=time, loc=loc)
                else:
                    response_format = self.config.get('response_format_noloc')
                    response = response_format.format(status=status, date=date, time=time)
                responses.append(response)
        except Exception as err:
            log.error("Parse error: {}".format(err))

        return ["\n".join(responses), r.status_code]

    def handle_aeropaq(self, tracking_number):
        base_url = self.config.get('aeropaq_baseurl')
        params = {'id': tracking_number}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            return [None, r.status_code]

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            for td in soup.select("td[class=dxgv]"):
                first_div, second_div = td.select("div")
                status = first_div.select_one("span").contents[0]
                date = second_div.contents[0].strip().replace('.', '-')
                time = second_div.contents[2].strip().upper()

                if len(second_div.contents) >= 4:
                    response_format = self.config.get('response_format')
                    loc = second_div.contents[4].strip() if len(second_div.contents) >= 4 else 'Desconocido'
                    response = response_format.format(status=status, date=date, time=time, loc=loc)
                else:
                    response_format = self.config.get('response_format_noloc')
                    response = response_format.format(status=status, date=date, time=time)
                responses.append(response)
        except Exception as err:
            log.error("Parse error: {}".format(err))

        return ["\n".join(responses), r.status_code]

    def handle_liberty(self, tracking_number):
        base_url = self.config.get('liberty_baseurl')
        params = {'id': tracking_number}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            return [None, r.status_code]

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            for td in soup.select("td[class=dxgv]"):
                first_div, second_div = td.select("div")
                status = first_div.select_one("span").contents[0]
                date = second_div.contents[0].strip().replace('.', '-')
                time = second_div.contents[2].strip().upper()

                if len(second_div.contents) >= 4:
                    response_format = self.config.get('response_format')
                    loc = second_div.contents[4].strip() if len(second_div.contents) >= 4 else 'Desconocido'
                    response = response_format.format(status=status, date=date, time=time, loc=loc)
                else:
                    response_format = self.config.get('response_format_noloc')
                    response = response_format.format(status=status, date=date, time=time)
                responses.append(response)
        except Exception as err:
            log.error("Parse error: {}".format(err))

        return ["\n".join(responses), r.status_code]

    def handle_caripack(self, tracking_number):
        base_url = self.config.get('caripack_baseurl')
        params = {'id': tracking_number}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            return [None, r.status_code]

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            for td in soup.select("td[class=dxgv]"):
                first_div, second_div = td.select("div")
                status = first_div.select_one("span").contents[0]
                date = second_div.contents[0].strip().replace('.', '-')
                time = second_div.contents[2].strip().upper()

                if len(second_div.contents) >= 4:
                    response_format = self.config.get('response_format')
                    loc = second_div.contents[4].strip() if len(second_div.contents) >= 4 else 'Desconocido'
                    response = response_format.format(status=status, date=date, time=time, loc=loc)
                else:
                    response_format = self.config.get('response_format_noloc')
                    response = response_format.format(status=status, date=date, time=time)
                responses.append(response)
        except Exception as err:
            log.error("Parse error: {}".format(err))

        return ["\n".join(responses), r.status_code]

    def handle_picknsend(self, tracking_number):
        base_url = self.config.get('picknsend_baseurl')
        params = {'id': tracking_number}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            return [None, r.status_code]

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            labels = soup.select("td[class=dxgv] label")
            label_pairs = [labels[i:i + 2] for i in range(0, len(labels), 2)]
            for first_label, second_label in label_pairs:
                status = first_label.contents[0]
                st, loc, datetime = [x.strip() for x in second_label.contents[0].split(',')]
                date, time = [x.strip() for x in datetime.split('|')]
                date = date.replace('.', '-')
                time = time.upper()
                loc = loc.upper()
                response_format = self.config.get('response_format')
                response = response_format.format(status=status, date=date, time=time, loc=loc)
                responses.append(response)
        except Exception as err:
            log.error("Parse error: {}".format(err))

        return ["\n".join(responses), r.status_code]

    def handle_domex(self, tracking_number):
        base_url = self.config.get('domex_baseurl')
        params = {'id': tracking_number}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            return [None, r.status_code]

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            for td in soup.select("td[class=dxgv]"):
                first_div, second_div = td.select("div")
                status = first_div.select_one("span").contents[0]
                date = second_div.contents[0].strip().replace('.', '-')
                time = second_div.contents[2].strip().upper()

                if len(second_div.contents) >= 4:
                    response_format = self.config.get('response_format')
                    loc = second_div.contents[4].strip() if len(second_div.contents) >= 4 else 'Desconocido'
                    response = response_format.format(status=status, date=date, time=time, loc=loc)
                else:
                    response_format = self.config.get('response_format_noloc')
                    response = response_format.format(status=status, date=date, time=time)
                responses.append(response)
        except Exception as err:
            log.error("Parse error: {}".format(err))

        return ["\n".join(responses), r.status_code]


    @classmethod
    def add_tracked_package(cls, *args, **kwargs):
        try:
            tp = TrackedPackage(**kwargs)
            tp.save()
            return True
        except Exception as ex:
            log.error('Unable to add tracked package. Reason: {}'.format(ex.message))
            return False

    @classmethod
    def fetch_tracked_package(cls, tracking_number):
        try:
            return TrackedPackage.by_tracking_number(tracking_number)
        except:
            return None

    def subscribe(self, tracking_number, user_id, notify=False):
        def do_notify():
            self.adapter.bot.sendMessage(chat_id=user_id,
                                         text="✅ You are now subscribed to receive updates for {}.".format(tracking_number))

        tp = TrackedPackage.by_tracking_number(tracking_number)
        if tp is None:
            subscribers = [user_id]
            tp = TrackedPackage(tracking_number=tracking_number,
                                subscribers=subscribers)
            tp.save()
            if notify:
                do_notify()
            return True
        elif tp.date_deleted is None:
            if user_id not in tp.subscribers:
                tp.subscribers.append(user_id)
                tp.save()
                if notify:
                    do_notify()
                return True
            else:
                if notify:
                    self.adapter.bot.sendMessage(chat_id=user_id,
                                                 text="❌ You are already subscribed.")
        else:
            if notify:
                self.adapter.bot.sendMessage(chat_id=user_id,
                                             text="❌ You can no longer subscribe to this package.")
        return False

    def unsubscribe(self, tracking_number, user_id, notify=False):
        tp = TrackedPackage.by_tracking_number(tracking_number)
        if tp is None or tp.date_deleted is not None:
            if notify:
                self.adapter.bot.sendMessage(chat_id=user_id,
                                             text="❌ Tracked package does not exist or was deleted.")
        else:
            if user_id not in tp.subscribers:
                if notify:
                    self.adapter.bot.sendMessage(chat_id=user_id,
                                                 text="❌ You are not subscribed to {}.".format(tracking_number))
            else:
                tp.subscribers = [subscriber for subscriber in tp.subscribers if subscriber != user_id]
                tp.save()
                if notify:
                    self.adapter.bot.sendMessage(chat_id=user_id,
                                                 text="🚮 You are now unsubscribed from receiving updates for {}.".format(tracking_number))
                return True
        return False

    def on_unsubscribe_button(self, update, *args, **kwargs):
        query = update.callback_query
        tracking_number = query.data.split(":")[2]
        user_id = query.from_user.id
        unsubscribed = self.unsubscribe(tracking_number, user_id, False)
        query.answer("Unsubscribed" if unsubscribed else "Failed")

    def on_subscribe_button(self, update, *args, **kwargs):
        query = update.callback_query
        tracking_number = query.data.split(":")[2]
        user_id = query.from_user.id
        subscribed = self.subscribe(tracking_number, user_id, False)
        query.answer("Subscribed" if subscribed else "Failed")

    def on_track_command(self, update, *args, **kwargs):
        tracking_number = kwargs.get('id')
        msg = update.message.reply_text("⌛ Parsing tracking number {}...".format(tracking_number))
        handled = False

        # Build keyboard
        buttons = [
            {"text": "➕ Subscribe", "callback_data": "{}:subscribe:{}".format(self.name, tracking_number)},
            {"text": "➖ Unsubscribe", "callback_data": "{}:unsubscribe:{}".format(self.name, tracking_number)},
        ]
        keyboard = [list(map(lambda btn: InlineKeyboardButton(**btn), buttons))]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = {
            "message_id": msg.message_id,
            "chat_id": update.message.chat.id,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        }
        if not any([courier['pattern'].match(tracking_number) for courier in self.couriers]):
            message["text"] = "❌ Given tracking number is not supported."
            self.adapter.bot.editMessageText(**message)

        for courier in self.couriers:
            m = courier['pattern'].match(tracking_number)
            if not m:
                continue

            message["text"] = "⌛ Fetching updates from {} for {}...".format(courier['name'], tracking_number)
            self.adapter.bot.editMessageText(**message)

            result, status = courier['handler'](tracking_number)
            if status == 200:
                if len(result) == 0:
                    message["text"] = "❌ Invalid tracking number for *{}* or no updates available at this time.".format(courier['name'])
                    self.adapter.bot.editMessageText(**message)
                else:
                    message["text"] = "🔔 *Updates for {}:*\n\n{}".format(tracking_number, result)
                    self.adapter.bot.editMessageText(**message)
                    if self.config.get('auto_subscribe'):
                        user_id = update.message.from_user.id
                        self.subscribe(tracking_number, user_id, False)
            else:
                message["text"] = "❌ Service is unavailable for {} at this time. Please try later.".format(courier['name'])
                self.adapter.bot.editMessageText(**message)

            break


def process_tracked_packages():
    plugin = process_tracked_packages.plugin

    def notify_subscribers(trackedPackage, message):
        for subscriber in trackedPackage.subscribers:
            plugin.adapter.bot.sendMessage(chat_id=subscriber,
                                           text=message,
                                           parse_mode='Markdown')

    def process_tracked_package(trackedPackage):
        tracking_number = trackedPackage.tracking_number
        # If no subscribers, skip
        if len(trackedPackage.subscribers) == 0:
            return
        # Delete TrackedPackage and return if tracking number isn't valid
        # What the... why didn't we store the courier in the 1st place?
        # 'Cause reasons!
        if not any([courier['pattern'].match(tracking_number) for courier in plugin.couriers]):
            trackedPackage.date_deleted = localized_date()
            trackedPackage.save()
            log.error('Deleted TrackedPackage {} because tracking number {} did not match any couriers.'.format(trackedPackage._id, tracking_number))
            return

        for courier in plugin.couriers:
            m = courier['pattern'].match(tracking_number)
            if not m:
                continue

            # Call handler
            result, status = courier['handler'](tracking_number)
            # Update last time the page was fetched
            trackedPackage.date_page_fetched = localized_date()
            trackedPackage.save()
            if status == 200:

                if len(result) == 0:
                    # Delete TrackedPackage if no results and notify subscribers
                    trackedPackage.date_deleted = localized_date()
                    trackedPackage.save()
                    notify_subscribers(trackedPackage, "🚮 You have been unsubscribed from updates for {}.\nNo updates are available.".format(tracking_number))

                elif result != trackedPackage.updates:
                    # Notify subscribers of new results
                    trackedPackage.updates = result
                    trackedPackage.num_errors = 0
                    trackedPackage.date_updated = localized_date()
                    trackedPackage.save()
                    notify_subscribers(trackedPackage, "🔔 *Updates for {}:*\n\n{}".format(tracking_number, result))
                else:
                    dtu = localized_date() - trackedPackage.date_updated if trackedPackage.date_updated is not None else None
                    if dtu is not None and (dtu.total_seconds() / (24 * 60 * 60)) >= plugin.config.get('max_days_stalled'):
                        trackedPackage.date_deleted = localized_date()
                        trackedPackage.save()
                        notify_subscribers(trackedPackage, "🚮 You have been unsubscribed from updates for {}.\nNo updates since {}.".format(tracking_number, trackedPackage.date_updated))
                    # No change, verify dates
            else:
                # Delete TrackedPackage if too many errors and notify subscribers
                if trackedPackage.num_errors is not None and trackedPackage.num_errors > plugin.config.get('max_num_errors'):
                    trackedPackage.date_deleted = localized_date()
                    trackedPackage.save()
                    notify_subscribers(trackedPackage, "🚮 You have been unsubscribed to receive updates for {}.".format(tracking_number))
                else:
                    # Increase num errors
                    trackedPackage.num_errors = trackedPackage.num_errors + 1 if trackedPackage.num_errors is not None else 1
                    trackedPackage.save()

            break

    tps = TrackedPackage.all()
    for tp in tps:
        process_tracked_package(tp)
    adapter = process_tracked_packages.adapter
