# -*- coding: utf-8 -*-
from marvinbot.utils import localized_date, get_message
from marvinbot.handlers import CommandHandler
from marvinbot.signals import plugin_reload
from marvinbot.plugins import Plugin
from marvinbot.models import User
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
            'response_format': '{date} {time}: {status} @ {loc}',
            'response_format_noloc': '{date} {time}: {status}',
            'bmcargo_baseurl': 'http://erp-online.bmcargo.com/zz/estatus.aspx',
            'bmcargo_pattern': r'^WR01-\d{9}$',
            'aeropaq_baseurl': 'http://erp-online.aeropaq.com/zz/estatus.aspx',
            'aeropaq_pattern': r'^WR02-\d{9}$',
            'picknsend_baseurl': 'http://online.picknsend.com/zz/estatus.aspx',
            'picknsend_pattern': r'^WR13-\d{9}$',
        }

    def configure(self, config):
        self.couriers = [
            {
                'name': 'bmcargo',
                'handler': self.handle_bmcargo,
                'pattern': re.compile(config.get('bmcargo_pattern'),
                                      flags=re.IGNORECASE)
            },
            {
                'name': 'aeropaq',
                'handler': self.handle_aeropaq,
                'pattern': re.compile(config.get('aeropaq_pattern'),
                                      flags=re.IGNORECASE)
            },
            {
                'name': 'picknsend',
                'handler': self.handle_picknsend,
                'pattern': re.compile(config.get('picknsend_pattern'),
                                      flags=re.IGNORECASE)
            }
        ]
        self.config = config

    def setup_handlers(self, adapter):
        self.add_handler(CommandHandler('track', self.on_track_command, command_description='Allows the user to track couriers packages.')
                         .add_argument('id', help='Tracking ID (e.g. WR01-001231234).'))

    def setup_schedules(self, adapter):
        pass

    def handle_bmcargo(self, update, *args, **kwargs):
        base_url = self.config.get('bmcargo_baseurl')
        _id = kwargs.get('id')
        params = {'id': _id}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            update.message.reply_text('❌ Unable to make the request.')
            return

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            for td in soup.select("td[class=dxgv]"):
                first_div, second_div = td.select("div")
                status = first_div.select_one("span").contents[0]
                date = second_div.contents[0].strip()
                time = second_div.contents[2].strip()

                if len(second_div.contents) >= 4:
                    response_format = self.config.get('response_format')
                    loc = second_div.contents[4].strip() if len(second_div.contents) >= 4 else 'Desconocido'
                    response = response_format.format(status=status, date=date, time=time, loc=loc)
                else:
                    response_format = self.config.get('response_format_noloc')
                    response = response_format.format(status=status, date=date, time=time)
                responses.append(response)
        except Exception as err:
            responses.append("Parse error: {}".format(err))

        if len(responses) == 0:
            update.message.reply_text("❌ Invalid tracking ID for *BMCargo* or no updates available at this time.",
                                     parse_mode="Markdown")
        else:
            update.message.reply_text("\n".join(responses))

    def handle_aeropaq(self, update, *args, **kwargs):
        base_url = self.config.get('aeropaq_baseurl')
        _id = kwargs.get('id')
        params = {'id': _id}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            update.message.reply_text('❌ Unable to make the request.')
            return

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            for td in soup.select("td[class=dxgv]"):
                first_div, second_div = td.select("div")
                status = first_div.select_one("span").contents[0]
                date = second_div.contents[0].strip()
                time = second_div.contents[2].strip()

                if len(second_div.contents) >= 4:
                    response_format = self.config.get('response_format')
                    loc = second_div.contents[4].strip() if len(second_div.contents) >= 4 else 'Desconocido'
                    response = response_format.format(status=status, date=date, time=time, loc=loc)
                else:
                    response_format = self.config.get('response_format_noloc')
                    response = response_format.format(status=status, date=date, time=time)
                responses.append(response)
        except Exception as err:
            responses.append("Parse error: {}".format(err))

        if len(responses) == 0:
            update.message.reply_text("❌ Invalid tracking ID for *Aeropaq* or no updates available at this time.",
                                     parse_mode="Markdown")
        else:
            update.message.reply_text("\n".join(responses))


    def handle_picknsend(self, update, *args, **kwargs):
        base_url = self.config.get('picknsend_baseurl')
        _id = kwargs.get('id')
        params = {'id': _id}
        r = requests.get(base_url, params=params)
        if r.status_code != 200:
            update.message.reply_text('❌ Unable to make the request.')
            return

        soup = BeautifulSoup(r.text, 'html.parser')
        responses = []
        try:
            labels = soup.select("td[class=dxgv] label")
            label_pairs = [labels[i:i + 2] for i in range(0, len(labels), 2)]
            for first_label, second_label in label_pairs:
                status = first_label.contents[0]
                st, loc, datetime = [x.strip() for x in second_label.contents[0].split(',')]
                date, time = [x.strip() for x in datetime.split('|')]
                response_format = self.config.get('response_format')
                response = response_format.format(status=status, date=date, time=time, loc=loc)
                responses.append(response)
        except Exception as err:
            responses.append("Parse error: {}".format(err))

        if len(responses) == 0:
            update.message.reply_text("❌ Invalid tracking ID for *PickNSend* or no updates available at this time.",
                                     parse_mode="Markdown")
        else:
            update.message.reply_text("\n".join(responses))


    def on_track_command(self, update, *args, **kwargs):
        _id = kwargs.get('id')

        handled = False
        for courier in self.couriers:
            m = courier['pattern'].match(_id)
            if m:
                courier['handler'](update, *args, **kwargs)
                handled = True
                break
        if not handled:
            update.message.reply_text("❌ Given tracking ID is not supported.")
