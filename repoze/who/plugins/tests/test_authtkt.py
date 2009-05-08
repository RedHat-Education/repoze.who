import unittest

class TestAuthTktCookiePlugin(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
        return AuthTktCookiePlugin

    def _makeEnviron(self, kw=None):
        environ = {'wsgi.version': (1,0)}
        if kw is not None:
            environ.update(kw)
        environ['REMOTE_ADDR'] = '1.1.1.1'
        environ['SERVER_NAME'] = 'localhost'
        return environ

    def _makeOne(self, *arg, **kw):
        plugin = self._getTargetClass()(*arg, **kw)
        return plugin

    def _makeTicket(self, userid='userid', remote_addr='0.0.0.0',
                    tokens = [], userdata='userdata',
                    cookie_name='auth_tkt', secure=False):
        from paste.auth import auth_tkt
        ticket = auth_tkt.AuthTicket(
            'secret',
            userid,
            remote_addr,
            tokens=tokens,
            user_data=userdata,
            cookie_name=cookie_name,
            secure=secure)
        return ticket.cookie_value()

    def test_implements(self):
        from zope.interface.verify import verifyClass
        from repoze.who.interfaces import IIdentifier
        klass = self._getTargetClass()
        verifyClass(IIdentifier, klass)

    def test_identify_nocookie(self):
        plugin = self._makeOne('secret')
        environ = self._makeEnviron()
        result = plugin.identify(environ)
        self.assertEqual(result, None)
        
    def test_identify_good_cookie_include_ip(self):
        plugin = self._makeOne('secret', include_ip=True)
        val = self._makeTicket(remote_addr='1.1.1.1')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % val})
        result = plugin.identify(environ)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], [''])
        self.assertEqual(result['repoze.who.userid'], 'userid')
        self.assertEqual(result['userdata'], 'userdata')
        self.failUnless('timestamp' in result)
        self.assertEqual(environ['REMOTE_USER_TOKENS'], [''])
        self.assertEqual(environ['REMOTE_USER_DATA'],'userdata')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_dont_include_ip(self):
        plugin = self._makeOne('secret', include_ip=False)
        val = self._makeTicket()
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % val})
        result = plugin.identify(environ)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], [''])
        self.assertEqual(result['repoze.who.userid'], 'userid')
        self.assertEqual(result['userdata'], 'userdata')
        self.failUnless('timestamp' in result)
        self.assertEqual(environ['REMOTE_USER_TOKENS'], [''])
        self.assertEqual(environ['REMOTE_USER_DATA'],'userdata')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_int_useridtype(self):
        plugin = self._makeOne('secret', include_ip=False)
        val = self._makeTicket(userid='1', userdata='userid_type:int')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % val})
        result = plugin.identify(environ)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], [''])
        self.assertEqual(result['repoze.who.userid'], 1)
        self.assertEqual(result['userdata'], 'userid_type:int')
        self.failUnless('timestamp' in result)
        self.assertEqual(environ['REMOTE_USER_TOKENS'], [''])
        self.assertEqual(environ['REMOTE_USER_DATA'],'userid_type:int')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_good_cookie_unknown_useridtype(self):
        plugin = self._makeOne('secret', include_ip=False)
        val = self._makeTicket(userid='userid', userdata='userid_type:unknown')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % val})
        result = plugin.identify(environ)
        self.assertEqual(len(result), 4)
        self.assertEqual(result['tokens'], [''])
        self.assertEqual(result['repoze.who.userid'], 'userid')
        self.assertEqual(result['userdata'], 'userid_type:unknown')
        self.failUnless('timestamp' in result)
        self.assertEqual(environ['REMOTE_USER_TOKENS'], [''])
        self.assertEqual(environ['REMOTE_USER_DATA'],'userid_type:unknown')
        self.assertEqual(environ['AUTH_TYPE'],'cookie')

    def test_identify_bad_cookie(self):
        plugin = self._makeOne('secret', include_ip=True)
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=bogus'})
        result = plugin.identify(environ)
        self.assertEqual(result, None)
    
    def test_remember_creds_same(self):
        plugin = self._makeOne('secret')
        val = self._makeTicket(userid='userid')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % val})
        result = plugin.remember(environ, {'repoze.who.userid':'userid',
                                           'userdata':'userdata'})
        self.assertEqual(result, None)

    def test_remember_creds_different(self):
        plugin = self._makeOne('secret')
        old_val = self._makeTicket(userid='userid')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % old_val})
        new_val = self._makeTicket(userid='other', userdata='userdata')
        result = plugin.remember(environ, {'repoze.who.userid':'other',
                                           'userdata':'userdata'})
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0],
                         ('Set-Cookie',
                          'auth_tkt="%s"; Path=/' % new_val))
        self.assertEqual(result[1],
                         ('Set-Cookie',
                           'auth_tkt="%s"; Path=/; Domain=localhost'
                            % new_val))
        self.assertEqual(result[2],
                         ('Set-Cookie',
                           'auth_tkt="%s"; Path=/; Domain=.localhost'
                            % new_val))

    def test_remember_creds_different_include_ip(self):
        plugin = self._makeOne('secret', include_ip=True)
        old_val = self._makeTicket(userid='userid', remote_addr='1.1.1.1')
        environ = self._makeEnviron({'HTTP_COOKIE': 'auth_tkt=%s' % old_val})
        new_val = self._makeTicket(userid='other',
                                   userdata='userdata',
                                   remote_addr='1.1.1.1')
        result = plugin.remember(environ, {'repoze.who.userid':'other',
                                           'userdata':'userdata'})
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0],
                         ('Set-Cookie',
                          'auth_tkt="%s"; Path=/' % new_val))
        self.assertEqual(result[1],
                         ('Set-Cookie',
                           'auth_tkt="%s"; Path=/; Domain=localhost'
                            % new_val))
        self.assertEqual(result[2],
                         ('Set-Cookie',
                           'auth_tkt="%s"; Path=/; Domain=.localhost'
                            % new_val))

    def test_remember_creds_different_bad_old_cookie(self):
        plugin = self._makeOne('secret')
        old_val = 'BOGUS'
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % old_val})
        new_val = self._makeTicket(userid='other', userdata='userdata')
        result = plugin.remember(environ, {'repoze.who.userid':'other',
                                           'userdata':'userdata'})
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0],
                         ('Set-Cookie',
                          'auth_tkt="%s"; Path=/' % new_val))
        self.assertEqual(result[1],
                         ('Set-Cookie',
                           'auth_tkt="%s"; Path=/; Domain=localhost'
                            % new_val))
        self.assertEqual(result[2],
                         ('Set-Cookie',
                           'auth_tkt="%s"; Path=/; Domain=.localhost'
                            % new_val))

    def test_remember_creds_different_with_nonstring_tokens(self):
        plugin = self._makeOne('secret')
        old_val = self._makeTicket(userid='userid')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % old_val})
        new_val = self._makeTicket(userid='other',
                                   userdata='userdata',
                                   tokens='foo,bar',
                                  )
        result = plugin.remember(environ, {'repoze.who.userid': 'other',
                                           'userdata': 'userdata',
                                           'tokens': ['foo', 'bar'],
                                          })
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0],
                         ('Set-Cookie',
                          'auth_tkt="%s"; Path=/' % new_val))
        self.assertEqual(result[1],
                         ('Set-Cookie',
                           'auth_tkt="%s"; Path=/; Domain=localhost'
                            % new_val))
        self.assertEqual(result[2],
                         ('Set-Cookie',
                           'auth_tkt="%s"; Path=/; Domain=.localhost'
                            % new_val))

    def test_remember_creds_different_int_userid(self):
        plugin = self._makeOne('secret')
        old_val = self._makeTicket(userid='userid')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % old_val})
        new_val = self._makeTicket(userid='1', userdata='userid_type:int')
        result = plugin.remember(environ, {'repoze.who.userid':1,
                                           'userdata':''})
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0],
                         ('Set-Cookie',
                          'auth_tkt="%s"; Path=/' % new_val))

    def test_remember_creds_different_long_userid(self):
        plugin = self._makeOne('secret')
        old_val = self._makeTicket(userid='userid')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % old_val})
        new_val = self._makeTicket(userid='1', userdata='userid_type:int')
        result = plugin.remember(environ, {'repoze.who.userid':long(1),
                                           'userdata':''})
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0],
                         ('Set-Cookie',
                          'auth_tkt="%s"; Path=/' % new_val))

    def test_remember_creds_different_unicode_userid(self):
        plugin = self._makeOne('secret')
        old_val = self._makeTicket(userid='userid')
        environ = self._makeEnviron({'HTTP_COOKIE':'auth_tkt=%s' % old_val})
        userid = unicode('\xc2\xa9', 'utf-8')
        new_val = self._makeTicket(userid=userid.encode('utf-8'),
                                   userdata='userid_type:unicode')
        result = plugin.remember(environ, {'repoze.who.userid':userid,
                                           'userdata':''})
        self.assertEqual(type(result[0][1]), str)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0],
                         ('Set-Cookie',
                          'auth_tkt="%s"; Path=/' % new_val))

    def test_forget(self):
        plugin = self._makeOne('secret')
        environ = self._makeEnviron()
        headers = plugin.forget(environ, None)
        self.assertEqual(len(headers), 3)
        header = headers[0]
        name, value = header
        self.assertEqual(name, 'Set-Cookie')
        self.assertEqual(value, 'auth_tkt=""""; Path=/')
        header = headers[1]
        name, value = header
        self.assertEqual(name, 'Set-Cookie')
        self.assertEqual(value, 'auth_tkt=""""; Path=/; Domain=localhost')
        header = headers[2]
        name, value = header
        self.assertEqual(name, 'Set-Cookie')
        self.assertEqual(value, 'auth_tkt=""""; Path=/; Domain=.localhost')

    def test_factory_wo_secret_wo_secretfile_raises_ValueError(self):
        from repoze.who.plugins.auth_tkt import make_plugin
        self.assertRaises(ValueError, make_plugin)

    def test_factory_w_secret_w_secretfile_raises_ValueError(self):
        from repoze.who.plugins.auth_tkt import make_plugin
        self.assertRaises(ValueError, make_plugin, 'secret', 'secretfile')

    def test_factory_w_bad_secretfile_raises_ValueError(self):
        from repoze.who.plugins.auth_tkt import make_plugin
        self.assertRaises(ValueError, make_plugin, secretfile='nonesuch.txt')

    def test_factory_w_secret(self):
        from repoze.who.plugins.auth_tkt import make_plugin
        plugin = make_plugin('secret')
        self.assertEqual(plugin.cookie_name, 'auth_tkt')
        self.assertEqual(plugin.secret, 'secret')
        self.assertEqual(plugin.include_ip, False)
        self.assertEqual(plugin.secure, False)

    def test_factory_w_secretfile(self):
        from tempfile import NamedTemporaryFile
        from repoze.who.plugins.auth_tkt import make_plugin
        ntf = NamedTemporaryFile()
        ntf.write('s33kr1t\n')
        ntf.flush()
        plugin = make_plugin(secretfile=ntf.name)
        self.assertEqual(plugin.secret, 's33kr1t')

