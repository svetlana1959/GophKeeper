import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, Navigate } from 'react-router-dom'
import { ArrowRight, Lock, Mail, UserPlus } from 'lucide-react'
import { apiErrorMessage } from '@/api/http'
import { useAuth } from '@/app/auth-context'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/form-field'
import { AuthCard, AuthDivider, AuthLayout } from './auth-layout'
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

  if (isAuthed) return <Navigate to="/dashboard" replace />

  const onSubmit = handleSubmit((values) => signup.mutate(values))

  return (
    <AuthLayout>
      <AuthCard
        icon={<UserPlus className="size-[54px]" strokeWidth={2.2} />}
        title="Create your account"
        subtitle="Join GophKeeper and keep your data secure."
      >
        <form onSubmit={onSubmit} noValidate className="flex flex-col">
          <div className="flex flex-col gap-5">
            <FormField
              label="Email"
              type="email"
              autoComplete="email"
              placeholder="Enter your email"
              icon={<Mail />}
              error={errors.email?.message}
              {...register('email')}
            />
            <FormField
              label="Password"
              type="password"
              autoComplete="new-password"
              placeholder="Create a strong password"
              icon={<Lock />}
              error={errors.password?.message}
              {...register('password')}
            />
            <FormField
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              placeholder="Confirm your password"
              icon={<Lock />}
              error={errors.confirmPassword?.message}
              {...register('confirmPassword')}
            />
          </div>

          {signup.isError ? (
            <p role="alert" className="text-destructive mt-4 text-sm">
              {apiErrorMessage(signup.error)}
            </p>
          ) : null}

          <Button
            type="submit"
            disabled={signup.isPending}
            className="relative mt-10 h-[43px] w-full text-[15px] font-medium"
          >
            {signup.isPending ? 'Creating account…' : 'Create account'}
            <ArrowRight className="absolute right-5 size-6" />
          </Button>

          <AuthDivider className="mt-6" />

          <p className="text-muted-foreground mt-6 text-center text-sm">
            Already have an account?{' '}
            <Link to="/login" className="text-primary font-semibold hover:underline">
              Log in
            </Link>
          </p>
        </form>
      </AuthCard>
    </AuthLayout>
  )
}
