/**
 * 继承链文件 - 深度 10
 */

import { InheritanceClass9 } from './InheritanceFile9';

export class InheritanceClass10 extends InheritanceClass9 {

    method0() {
        super.method0?.();
        return 'Inheritance 10 result';
    }


    method1() {
        super.method3?.();
        return 'Inheritance 10 result';
    }


    method2() {
        super.method0?.();
        return 'Inheritance 10 result';
    }


    method3() {
        super.method2?.();
        return 'Inheritance 10 result';
    }


    method4() {
        super.method3?.();
        return 'Inheritance 10 result';
    }


    method5() {
        super.method4?.();
        return 'Inheritance 10 result';
    }


    method6() {
        super.method2?.();
        return 'Inheritance 10 result';
    }


    method7() {
        super.method2?.();
        return 'Inheritance 10 result';
    }


    method8() {
        super.method2?.();
        return 'Inheritance 10 result';
    }

}
