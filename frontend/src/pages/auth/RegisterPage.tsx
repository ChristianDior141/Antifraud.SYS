import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { authApi } from '@/services/api';
import { Shield, AlertCircle, CheckCircle, Eye, EyeOff } from 'lucide-react';

type Strength = { score: 0 | 1 | 2 | 3; label: string; color: string; ok: boolean };

function passwordStrength(pw: string): Strength {
  if (!pw) return { score: 0, label: '', color: '', ok: false };
  const lower = /[a-z]/.test(pw);
  const upper = /[A-Z]/.test(pw);
  const digit = /[0-9]/.test(pw);
  const special = /[^A-Za-z0-9]/.test(pw);
  const reqMet = pw.length >= 8 && lower && upper && digit && special;
  if (!reqMet) return { score: 1, label: 'Слабый — не принимается', color: 'bg-red-500', ok: false };
  if (pw.length < 12) return { score: 2, label: 'Средний', color: 'bg-amber-500', ok: true };
  return { score: 3, label: 'Надёжный', color: 'bg-green-500', ok: true };
}

const schema = z.object({
  full_name: z.string().min(2, 'Full name required'),
  email: z.string().email('Valid email required'),
  phone_number: z.string()
    .regex(/^\+[1-9]\d{6,14}$/, 'International format required, e.g. +14155552671'),
  password: z.string().min(8, 'At least 8 characters')
    .regex(/[A-Z]/, 'Must contain uppercase')
    .regex(/[a-z]/, 'Must contain lowercase')
    .regex(/[0-9]/, 'Must contain digit')
    .regex(/[^A-Za-z0-9]/, 'Must contain a special character'),
  confirm_password: z.string(),
}).refine(d => d.password === d.confirm_password, {
  message: "Passwords don't match", path: ['confirm_password'],
});
type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const pwValue = watch('password') || '';
  const strength = passwordStrength(pwValue);

  const onSubmit = async (data: FormData) => {
    if (!passwordStrength(data.password).ok) {
      setError('Пароль слишком слабый. Нужен минимум средний уровень: 8+ символов, строчные и заглавные буквы, цифра и спецсимвол.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authApi.register({
        email: data.email, password: data.password,
        full_name: data.full_name, phone_number: data.phone_number,
      });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <CheckCircle className="mx-auto h-16 w-16 text-emerald-500" />
          <h2 className="mt-4 text-2xl font-bold text-gray-900">Account Created!</h2>
          <p className="mt-2 text-gray-500">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
          <div className="mb-6 text-center">
            <Shield className="mx-auto h-10 w-10 text-primary" />
            <h2 className="mt-3 text-2xl font-bold text-gray-900">Create your account</h2>
          </div>

          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {([
              { name: 'full_name', label: 'Full Name', type: 'text', placeholder: 'John Doe' },
              { name: 'email', label: 'Email', type: 'email', placeholder: 'you@example.com' },
              { name: 'phone_number', label: 'Phone Number', type: 'tel', placeholder: '+14155552671' },
            ] as const).map(({ name, label, type, placeholder }) => (
              <div key={name}>
                <label className="block text-sm font-medium text-gray-700">{label}</label>
                <input
                  {...register(name)}
                  type={type}
                  placeholder={placeholder}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
                {errors[name] && <p className="mt-1 text-xs text-red-600">{errors[name]?.message}</p>}
              </div>
            ))}

            {/* Password with show/hide + strength meter */}
            <div>
              <label className="block text-sm font-medium text-gray-700">Password</label>
              <div className="relative mt-1">
                <input
                  {...register('password')}
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 pr-10 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-gray-600">
                  {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {pwValue && (
                <div className="mt-2">
                  <div className="h-1.5 w-full overflow-hidden rounded bg-gray-200">
                    <div className={`h-1.5 rounded transition-all ${strength.color}`}
                      style={{ width: `${(strength.score / 3) * 100}%` }} />
                  </div>
                  <p className={`mt-1 text-xs ${strength.ok ? 'text-gray-500' : 'text-red-600'}`}>
                    Сложность: {strength.label}
                  </p>
                </div>
              )}
              <p className="mt-1 text-xs text-gray-400">
                Минимум 8 символов: строчные, заглавные, цифры и спецсимволы.
              </p>
              {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
            </div>

            {/* Confirm password with show/hide */}
            <div>
              <label className="block text-sm font-medium text-gray-700">Confirm Password</label>
              <div className="relative mt-1">
                <input
                  {...register('confirm_password')}
                  type={showConfirm ? 'text' : 'password'}
                  placeholder="••••••••"
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 pr-10 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
                <button type="button" onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-gray-600">
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.confirm_password && <p className="mt-1 text-xs text-red-600">{errors.confirm_password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-primary hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
