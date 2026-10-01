import styles from "./ui.module.css";

type PageIntroProps = {
  title: string;
  description: string;
};

export function PageIntro({ title, description }: PageIntroProps) {
  return (
    <header className={styles.pageIntro}>
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}
