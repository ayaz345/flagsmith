from trench.backends.application import ApplicationBackend


class CustomApplicationBackend(ApplicationBackend):
    def dispatch_message(self):
        original_message = super(CustomApplicationBackend, self).dispatch_message()
        return {**original_message, "secret": self.obj.secret}
