# Copyright (C) 2017 Jurriaan Bremer <jbr@cuckoo.sh>
# This file is part of HTTPReplay - http://jbremer.org/httpreplay/
# See the file 'LICENSE' for copying permission.

import os

from httpreplay.reader import PcapReader
from httpreplay.smegma import TCPPacketStreamer, TLSStream
from httpreplay.cut import smtp_handler
from httpreplay.cobweb import SmtpProtocol

class SmtpTest(object):
    handlers = {
        25: smtp_handler,
        587: smtp_handler,
    }

    def __init__(self, pcapfile):
        self.reader = PcapReader(open(pcapfile, "rb"))
        self.reader.tcp = TCPPacketStreamer(self.reader, self.handlers)

    def get_sent_recv(self):
        s, r = None, None
        for s, ts, prot, sent, recv in self.reader.process():
            s = sent
            r = recv
        return s, r

def test_read_smtp_from_to():
    test = SmtpTest(os.path.join("tests", "pcaps", "smtp-auth-login.pcap"))
    sent, recv = test.get_sent_recv()

    expected = [
        [b'xxxxxx@xxxxx.co.uk'],
        [b'xxxxxx.xxxx@xxxxx.com']
    ]

    output = [
        sent.mail_from,
        sent.mail_to
    ]
    assert expected == output

def test_read_smtp_headers():
    test = SmtpTest(os.path.join("tests", "pcaps", "smtp-auth-login.pcap"))
    sent, recv = test.get_sent_recv()
    assert sent.headers == {
        b'Reply-To': b'<xxxxxx@xxxxx.co.uk>',
        b'From': b'"WShark User" <xxxxxx@xxxxx.co.uk>',
        b'To': b'<xxxxxx.xxxx@xxxxx.com>',
        b'Subject': b'Test message for capture',
        b'Date': b'Sun, 24 Jun 2007 10:56:03 +0200',
        b'MIME-Version': b'1.0',
        b'Content-Type': b'multipart/mixed;',
        b'X-Mailer': b'Microsoft Office Outlook, Build 11.0.5510',
        b'Thread-Index': b'Ace2O6M0WGyVJP3rQCuQePVHKWo5Ag==',
        b'X-MimeOLE': b'Produced By Microsoft MimeOLE V6.00.2900.3138'
    }

def test_read_smtp_message_body():
    test = SmtpTest(os.path.join("tests", "pcaps", "smtp-auth-login.pcap"))
    sent, recv = test.get_sent_recv()
    assert sent.message[:48] == (
        b"This is a multi-part message in MIME format.\r\n\r\n"
    )

def test_get_username_password_auth_login():
    test = SmtpTest(os.path.join("tests", "pcaps", "smtp-auth-login.pcap"))
    sent, recv = test.get_sent_recv()
    assert sent.username == b"galunt"
    assert sent.password == b"V1v1tr0n"

def test_get_username_password_auth_login_arg():
    smtp = SmtpProtocol()
    smtp.init()

    smtp.parse_request(b"AUTH LOGIN Zm9vZEBiZWVyLnBseg==")
    smtp.rescode = 334
    smtp.message = b"UGFzc3dvcmQ6"
    smtp.parse_request(b"U2hvb3BEYVdob29wIQ==")

    assert smtp.request.username == b"food@beer.plz"
    assert smtp.request.password == b"ShoopDaWhoop!"

def test_get_username_password_auth_plain():
    smtp = SmtpProtocol()
    smtp.init()

    user_pass = b"AHRlc3R1c2VyAEF3M3MwbVA0enpzIQ=="
    smtp.rescode = 334
    smtp.request.auth_type = b"plain"
    smtp.parse_request(user_pass)
    assert smtp.request.username == b"testuser"
    assert smtp.request.password == b"Aw3s0mP4zzs!"

def test_get_username_password_auth_plain_arg():
    smtp = SmtpProtocol()
    smtp.init()

    smtp.parse_request(b"AUTH PLAIN AHRlc3R1c2VyAEF3M3MwbVA0enpzIQ==")
    assert smtp.request.username == b"testuser"
    assert smtp.request.password == b"Aw3s0mP4zzs!"

def test_get_username_cram_md5_challenge():
    smtp = SmtpProtocol()
    smtp.init()

    smtp.rescode = 334
    smtp.request.auth_type = b"cram-md5"
    smtp.parse_request(b"ZnJlZCA5ZTk1YWVlMDljNDBhZjJiODRhMGMyYjNiYmFlNzg2ZQ==")
    assert smtp.request.username == b"fred"
    assert smtp.request.password is None

def test_smtp_reply_ok_responses():
    test = SmtpTest(os.path.join("tests", "pcaps", "smtp-auth-login.pcap"))
    sent, recv = test.get_sent_recv()
    assert recv.ok_responses == [
        b"250-smtp006.mail.xxx.xxxxx.com",
        b"250-AUTH LOGIN PLAIN XYMCOOKIE",
        b"250-PIPELINING",
        b'250 8BITMIME',
        b"250 ok",
        b"250 ok",
        b"250 ok 1182675387 qp 77793",
    ]

def test_read_smtp_ready_message():
    test = SmtpTest(os.path.join("tests", "pcaps", "smtp-auth-login.pcap"))
    sent, recv = test.get_sent_recv()
    assert recv.ready_message == b"220 smtp006.mail.xxx.xxxxx.com ESMTP\r\n"

    # In case of starttls, status 220 is used twice. Test if the banner
    # is still extracted
    smtp = SmtpProtocol()
    smtp.init()
    smtp.parse_reply(b"220 example.com (Tosti01) ESMTP Service ready\r\n")
    smtp.parse_reply(
        b"250-example.com Hello WORKSTATION-42 [192.168.1.100]\r\n"
        b"250-AUTH LOGIN PLAIN\r\n"
        b"250-SIZE 69920427\r\n"
        b"250 STARTTLS\r\n"
    )
    smtp.parse_reply(b"220 OK STARTTLS ready\r\n")
    assert smtp.reply.ready_message == (
        b"220 example.com (Tosti01) ESMTP Service ready\r\n"
    )
