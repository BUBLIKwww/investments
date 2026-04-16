import { ApiError } from "@/shared/api/client";

export type UserFacingApiError = {
  title: string;
  message: string;
  isNetwork: boolean;
  status: number;
};

export function getUserFacingApiError(err: unknown): UserFacingApiError {
  if (err instanceof ApiError) {
    if (err.status === 0) {
      return {
        title: "Нет соединения",
        message: err.message,
        isNetwork: true,
        status: 0,
      };
    }
    if (err.status >= 500) {
      return {
        title: "Ошибка сервера",
        message: err.message,
        isNetwork: false,
        status: err.status,
      };
    }
    return {
      title: "Ошибка",
      message: err.message,
      isNetwork: false,
      status: err.status,
    };
  }
  if (err instanceof Error) {
    return { title: "Ошибка", message: err.message, isNetwork: false, status: 0 };
  }
  return { title: "Ошибка", message: "Неизвестная ошибка", isNetwork: false, status: 0 };
}
