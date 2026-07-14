import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, Navigate } from 'react-router-dom'
import { ArrowRight, LogIn, Lock, User } from 'lucide-react'
import { apiErrorMessage } from '@/api/http'
import { useAuth } from '@/app/auth-context'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/form-field'
import { AuthCard, AuthDivider, AuthLayout } from './auth-layout'
import { loginSchema, type LoginValues } from './login-schema'
import { useLogin } from './use-login'

export function LoginPage() {
  const { isAuthed } = useAuth()
  const login = useLogin()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })

  if (isAuthed) return <Navigate to="/" replace />

  const onSubmit = handleSubmit((values) => login.mutate(values))

  return (
    <AuthLayout>
      <AuthCard
        icon={<LogIn className="size-[54px]" strokeWidth={2.4} />}
        title="Log in to your account"
        subtitle="Welcome back! Please enter your details."
      >
        <form onSubmit={onSubmit} noValidate className="flex flex-col">
          <div className="flex flex-col gap-5">
            <FormField
              label="Username"
              autoComplete="username"
              placeholder="Enter your username"
              icon={<User />}
              error={errors.username?.message}
              {...register('username')}
            />
            <FormField
              label="Password"
              type="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              icon={<Lock />}
              error={errors.password?.message}
              {...register('password')}
            />
          </div>

          {login.isError ? (
            <p role="alert" className="text-destructive mt-4 text-sm">
              {apiErrorMessage(login.error)}
            </p>
          ) : null}

          <Button
            type="submit"
            disabled={login.isPending}
            className="relative mt-12 h-[43px] w-full text-[15px] font-medium"
          >
            {login.isPending ? 'Signing in…' : 'Log in'}
            <ArrowRight className="absolute right-5 size-6" />
          </Button>

          <AuthDivider className="mt-6" />

          <p className="text-muted-foreground mt-6 text-center text-sm">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="text-primary font-semibold hover:underline">
              Create account
            </Link>
          </p>
        </form>
      </AuthCard>
    </AuthLayout>
  )
}
