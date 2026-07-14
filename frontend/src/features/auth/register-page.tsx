import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, Navigate } from 'react-router-dom'
import { ArrowRight, Lock, Mail, UserPlus } from 'lucide-react'
import { apiErrorMessage } from '@/api/http'
import { useAuth } from '@/app/auth-context'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/form-field'
import { AuthCard, AuthLayout } from './auth-layout'
import { registerSchema, type RegisterValues } from './register-schema'
import { useRegister } from './use-register'

export function RegisterPage() {
  const { isAuthed } = useAuth()
  const signup = useRegister()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: '', password: '', confirmPassword: '' },
  })

  if (isAuthed) return <Navigate to="/" replace />

  const onSubmit = handleSubmit((values) => signup.mutate(values))

  return (
    <AuthLayout>
      <AuthCard
        icon={<UserPlus className="size-8" strokeWidth={2.5} />}
        title="Create your account"
        subtitle="Set up an account to manage your devices and secrets"
      >
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
          <FormField
            label="Email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            icon={<Mail />}
            error={errors.email?.message}
            {...register('email')}
          />
          <FormField
            label="Password"
            type="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            icon={<Lock />}
            error={errors.password?.message}
            {...register('password')}
          />
          <FormField
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            placeholder="Re-enter your password"
            icon={<Lock />}
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />

          {signup.isError ? (
            <p role="alert" className="text-destructive text-sm">
              {apiErrorMessage(signup.error)}
            </p>
          ) : null}

          <Button type="submit" disabled={signup.isPending} className="mt-1 h-11 justify-between">
            {signup.isPending ? 'Creating account…' : 'Create account'}
            <ArrowRight className="size-4" />
          </Button>
        </form>

        <p className="text-muted-foreground mt-6 text-center text-sm">
          Already have an account?{' '}
          <Link to="/login" className="text-primary font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </AuthCard>
    </AuthLayout>
  )
}
