/**
 * 继承链文件 - 深度 2
 */

import { InheritanceClass1 } from './InheritanceFile1';

export class InheritanceClass2 extends InheritanceClass1 {

    method0() {
        super.method5?.();
        return 'Inheritance 2 result';
    }


    method1() {
        super.method5?.();
        return 'Inheritance 2 result';
    }


    method2() {
        super.method1?.();
        return 'Inheritance 2 result';
    }


    method3() {
        super.method5?.();
        return 'Inheritance 2 result';
    }


    method4() {
        super.method0?.();
        return 'Inheritance 2 result';
    }


    method5() {
        super.method1?.();
        return 'Inheritance 2 result';
    }


    method6() {
        super.method0?.();
        return 'Inheritance 2 result';
    }


    method7() {
        super.method0?.();
        return 'Inheritance 2 result';
    }


    method8() {
        super.method5?.();
        return 'Inheritance 2 result';
    }


    method9() {
        super.method5?.();
        return 'Inheritance 2 result';
    }


    method10() {
        super.method0?.();
        return 'Inheritance 2 result';
    }

}
